from tkinter import Button

def initialLayout(parent):
    test1Button = Button(parent, text="Test 1", width=10, height=10)
    test2Button = Button(parent, text="Test 2", width=10, height=10)

    test1Button.grid(row=0, padx=50, pady=50)
    test2Button.grid(row=0, column=1, padx=50, pady=50)
