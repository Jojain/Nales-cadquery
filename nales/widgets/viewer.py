
from PySide6.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout
from cq_viewer.widgets.occt_widget import OCCTWidget

# pour collapse les qsplitter
#https://stackoverflow.com/questions/19832481/how-to-control-qsplitter-handle-using-buttons

class Viewer(QTabWidget):
    def __init__(self, parent = None):
        super(Viewer, self).__init__(parent)
        self.views = []
        self.current_view = None
        self.setTabsClosable(True)
        # self.setMovable(True)
        self.tabBarAutoHide()
        self.view_state = 1

    def _set_initials_views(self):
        for i in range(4):
            self.views.append(OCCTWidget(self))

    def add_view(self, view_name):        
        container = QWidget(self)
        new_view = OCCTWidget(self)
        layout = QHBoxLayout(container)
        layout.addWidget(new_view)

        self.views.append(new_view)
        self.addTab(container, view_name)
        self.current_view = new_view
        self.setCurrentWidget(container)


    def render(self, obj):
        self.current_view.context.Display(obj, True)
        self.current_view.fit()

    def _set_double_view(self):
        if self.count() < 2 : return


        index = self.currentIndex()
        label = self.tabText(index)
        view1 = self.views[index-1]
        view2 = self.views[index]
        view1.fit()
        view2.fit()

        double_view = QWidget(self)
        layout = QHBoxLayout(double_view)

        layout.addWidget(view1)
        layout.addWidget(view2)

        self.removeTab(index)
        self.removeTab(index)

        self.insertTab(1, double_view, label)

        

