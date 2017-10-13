from tkinter import Tk, Frame
from app import App
from app import startBCI


if __name__ == '__main__':
    #Start reading from BCI
    startBCI()
    #Main window
    app = App()
    w, h = app.winfo_screenwidth(), app.winfo_screenheight()
    app.geometry("%dx%d+0+0" % (w, h)) 
    app.configure(bg='black')

    app.title('')
    app.mainloop()

