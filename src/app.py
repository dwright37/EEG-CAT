import tkinter as tk
from NeuroPy import NeuroPy
from tkinter import messagebox 
import json
from PIL import ImageTk, Image
#import ipdb
import random
import os
import logging
import uuid
import time
import collections
import numpy as np

LOGGER = logging.getLogger('cse216_project')
LOGGER.setLevel(logging.DEBUG)

FONT_SIZE=15
TESTS_DIR='./test'
MAX_DIFF = 4
MIN_DIFF = 1
attention = collections.deque([], 20)

def attention_callback(attention_lvl):
    attention.appendleft(attention_lvl)
    LOGGER.debug('IA; absolute: ' + str(attention_lvl) + '; windowAverage: ' + np.mean(attention))
    return None

def startBCI():
    object1=NeuroPy("COM6") 
    #set call back:
    object1.setCallBack("attention",attention_callback)
    
    #start method
    object1.start()
    return None

class App(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        container = tk.Frame(self, bg='white') 
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (StartFrame, TestFrame, EndFrame):
            page_name = F.__name__
            frame = F(container, self)
            self.frames[page_name] = frame

            frame.grid(row=0, column=0, sticky='nsew')

        self.showFrame('StartFrame')

        self.submittedAnswers = []
        self.answerCorrect = []
        self.currDiff = 0

    def showFrame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

    def loadQuestion(self, frame, data):
        self.currentQuestion = data
        frame.loadQuestionView(self.testContextDir, data)
        self.currT = int(round(time.time() * 1000))

    def startTest(self, test=1):
        self.showFrame('TestFrame')
        self.ordering = test
        if test == 2 or test == 3:
            self.attention = np.mean(attention)
        else:
            self.attention = 0
        self.testContextDir = TESTS_DIR + '/' + str(test)
        self._organizeQuestions(test)
        self.findAndLoadNextQuestion(self.frames['TestFrame'])
        self.startLogging(test)
        self.startTime = int(round(time.time() * 1000))

    def startLogging(self, test=1):
        if test == 1:
            logDir = './eval/control'
            typeName = 'CONTROL'
        else:
            logDir = './eval/experimental'
            typeName = 'EXPERIMENTAL'

        self.testId = uuid.uuid4()
        fh = logging.FileHandler(logDir + '/' + str(self.testId) + '.log')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        LOGGER.addHandler(fh)

        LOGGER.info('Starting test, ID is ' + str(self.testId) + ',' + typeName)

    def _organizeQuestions(self, ordering=1):
        '''
           Internally organize all of the questions to make
           selection easier
        '''
        json_files = [f for f in os.listdir(self.testContextDir) if f.endswith('json')]
        random.shuffle(json_files)
        numQs = 0
        if self.ordering == 1 or ordering == 3:
            self.questions = []

            for f in json_files:
                with open(self.testContextDir + '/' + f) as data_file:
                    data = json.load(data_file)
                self.questions.append(data)
            numQs = len(self.questions)
        else:
            self.questions = { '1': [], '2': [], '3': [], '4': [] }

            for f in json_files:
                with open(self.testContextDir + '/' + f) as data_file:
                    data = json.load(data_file)
                self.questions[str(data['difficulty'])].append(data)
                numQs += 1

        self.totalQuestions = numQs
        self.currQ = 1

    def submitAnswer(self, frame, answer=None):
        print(answer)
        if not answer:
            #Notify the user that they must select an answer
            messagebox.showinfo('Select answer', 'Please select an answer')
            return
    
        correctlyAnswered = answer == self.currentQuestion['answerValue']
        t = int(round(time.time() * 1000))

        #Record the answer


        self.submittedAnswers.append(answer)
        #Keep track of questions answered correctly
        self.answerCorrect.append(correctlyAnswered)

        if self.currQ < self.totalQuestions:
            self.logPerQuestionMetrics(self.currentQuestion, answer, t - self.currT)
            self.currQ += 1
            self.findAndLoadNextQuestion(frame)
        else:
            #Calculate score, log
            LOGGER.debug('Correct: ' + str(sum(self.answerCorrect)) + ' out of ' + str(self.totalQuestions))
            self.showFrame('EndFrame')

    def logPerQuestionMetrics(self, questionData, answer, timeToAnswer):
        LOGGER.debug('QUESTION; difficulty : ' + str(questionData['difficulty'])
                    +', correctAnswer : ' + questionData['answerValue']
                    +', userAnswer : ' + answer
                    +', correct : ' + str(int(answer == questionData['answerValue']))
                    +', timeToAnswer : ' + str(timeToAnswer) + ' ms'
                    +', startAttention : ' + str(self.attention)
                    +', endAttention : ' + str(np.mean(attention)))
 
    def findAndLoadNextQuestion(self, frame):
        #Get the next question
        #TODO: Implement question retrieval algorithm
        if self.ordering is 1:
            #Control
            self.loadQuestion(frame, self.questions.pop())
        elif self.ordering is 2:
            #Experimental condition 1
            theta = self.getTheta()
            attentive = self.getAttentionLevel(theta)
            question = self.getNextQuestionFromAttention(attentive)
            self.attention = np.mean(attention)
            print('Attention: ', attention, ', difficulty: ', question['difficulty'])
            self.loadQuestion(frame, question)
        elif self.ordering is 3:
            theta = self.getTheta()
            attentive = self.getAttentionLevel(theta)
            self.attention = np.mean(attention)
            if not attentive:
                frame.toggleColors() 
            self.loadQuestion(frame, self.questions.pop())
    
    def getTheta(self):
        return 20

    def getAttentionLevel(self, theta):
        currAttention = np.mean(attention)
        if currAttention < 20 or self.attention - currAttention >= theta:
            return False
        return True

    def getNextQuestionFromAttention(self, attentive = True):
        if self.currDiff == 0:
            #Start of test
            self.currDiff = 1
            return self.questions['1'].pop()

        currDiff = self.currDiff
        
        #Forward direction
        if attentive:
            #if currDiff < MAX_DIFF
            #    if len(self.questions[str(currDiff)]) < len(self.questions[str(currDiff + 1)]):
            #        #If current difficulty has less questions than next difficulty, advance to next difficulty if 
            #        #possible. Otherwise stay at current difficulty or move backwards if necessary
            #        newDiff = self._findNextQuestionForward(currDiff)

            #        if newDiff > MAX_DIFF:
            #            #No questions more difficult
            #            if len(self.questions[str(currDiff)]) is 0:
            #                newDiff = self._findNextQuestionBackwards(currDiff)
            #            else:
            #                newDiff = currDiff
            #    else:
            #        #If current difficulty has more questions than next difficulty, go back to previous difficulty if 
            #        #possible. Otherwise stay at current difficulty or move forwards if necessary
            #        newDiff = self._findNextQuestionBackward(currDiff)

            #        if newDiff < MIN_DIFF:
            #            #No questions more difficult
            #            if len(self.questions[str(currDiff)]) is 0:
            #                newDiff = self._findNextQuestionForwards(currDiff)
            #            else:
            #                newDiff = currDiff
            newDiff = self._findNextQuestionForward(currDiff)

            if newDiff > MAX_DIFF:
                #No questions more difficult
                if len(self.questions[str(currDiff)]) is 0:
                    newDiff = self._findNextQuestionBackward(currDiff)
                else:
                    newDiff = currDiff
        else:
            #Go to easiest possible question
            newDiff = MIN_DIFF - 1

            newDiff = self._findNextQuestionForward(newDiff)
    
        self.currDiff = newDiff
        return self.questions[str(newDiff)].pop()    
    
    def _findNextQuestionForward(self, startDiff):        
        newDiff = startDiff
        while newDiff < MAX_DIFF and len(self.questions[str(newDiff + 1)]) is 0:
            newDiff += 1

        return newDiff + 1

    def _findNextQuestionBackward(self, startDiff):
        newDiff = startDiff
        while newDiff > MIN_DIFF and len(self.questions[str(newDiff - 1)]) is 0:
            newDiff -= 1
    
        return newDiff - 1

class StartFrame(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent) 
        self.controller = controller

        self.test1Button = tk.Button(self, text="Test 1", width=10, height=10,
                                        command=lambda: controller.startTest(test=1))

        self.test2Button = tk.Button(self, text="Test 2", width=10, height=10,
                                        command=lambda: controller.startTest(test=2))
    
        self.test3Button = tk.Button(self, text="Test 3", width=10, height=10,

                                        command=lambda: controller.startTest(test=3))
        self.test1Button.grid(row=0, column=0, padx=50, pady=50)
        self.test2Button.grid(row=0, column=1, padx=50, pady=50)
        self.test3Button.grid(row=0, column=2, padx=50, pady=50)

class TestFrame(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.colors = True
        self.widgets = []
        self.controller = controller
 
        self.questionFrame = tk.Label(self, height=600)
        self.questionFrame.pack(fill=tk.BOTH, expand=1)
        self.widgets.append(self.questionFrame)

        self.answerFrame = tk.Frame(self, height=200)
        self.answerFrame.pack(fill=tk.BOTH, expand=1)
        self.widgets.append(self.answerFrame)

        self.selected = tk.StringVar()

        self.submitFrame = tk.Frame(self, height=100)
        self.submitFrame.pack(fill=tk.BOTH, expand=1)
        self.widgets.append(self.submitFrame)

        self.submitAnswerButton = tk.Button(self.submitFrame, 
                                            text="Submit", 
                                            width=10, 
                                            font=(None, FONT_SIZE),
                                            command=lambda: controller.submitAnswer(self, 
                                                                        answer=self.selected.get()))
        self.submitAnswerButton.pack(expand=1)
        self.setColors()
        #controller.loadQuestion(self, 1)


    def loadQuestionView(self, testDir, data):
        img = ImageTk.PhotoImage(Image.open(testDir + '/' + data['questionFile']))
        self.questionFrame['image'] = img
        self.questionFrame.img = img

        if hasattr(self, 'radioGroup'):
            self.radioGroup.pack_forget()
            self.radioGroup.destroy()

        bg = 'white' if self.colors else 'black'
        fg = 'black' if self.colors else 'white'

        self.radioGroup = tk.Frame(self.answerFrame, bg=bg)
        self.radioGroup.pack()
        self.radioGroup.opts = []
        #Load all the radio buttons
        for opt in data['options']:
            b = tk.Radiobutton(self.radioGroup, text=opt['text'], font=(None, FONT_SIZE),
                    variable=self.selected, value=opt['value'], anchor='nw', bg=bg, fg=fg, selectcolor=bg)
            b.pack(fill='both')
            self.radioGroup.opts.append(b)

        self.selected.set('')

    def toggleColors(self):
        self.colors = not self.colors
        self.setColors()

    def setColors(self):
        bg = 'white' if self.colors else 'black'
        for w in self.widgets:
            w.configure(bg=bg)

class EndFrame(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
 
        self.endText = tk.Label(self, text='Thank you', height=600, font=(None, 24))
        self.endText.pack(fill=tk.BOTH)

