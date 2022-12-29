from asyncio import sleep
from textual.app import App, ComposeResult
from textual.widgets import Static, ListView, ListItem, Label, Footer, Input, Button, Header
from textual.screen import Screen
from textual.containers import Container, Grid
from textual.reactive import reactive, watch
from rich.progress import Progress
from templates import Template, AERender
from projects import *


class ErrorMessage(Screen):
    _message: str

    def __init__(self, message: str, name: str | None = None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(name, id, classes)
        self._message = message

    def compose(self) -> ComposeResult:
        yield Grid(
            Static("There was an error in rendering the project."),
            Static(self._message),
            Button("OK", variant="primary", id="ok"),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "ok":
            self.app.pop_screen()


class ProgressBar(Static):
    _bar: Progress

    def __init__(self, task: str = ""):
        super().__init__("")
        self._bar = Progress()
        self._task_id = self._bar.add_task(task, total=1)

    def reset(self):
        self._bar.reset(self._task_id)
        self.update(self._bar)
    
    def update_progress(self, amount: float):
        self._bar.update(self._task_id, advance=amount)
        if self._bar.finished:
            self.update("Done!")
        else:
            self.update(self._bar)


class TemplateView(Container):
    template: Template

    def compose(self) -> ComposeResult:
        yield Container()

    def on_mount(self) -> None:
        watch(self.app, "selected_template", self.on_template_change, init=False)

    async def on_template_change(self, template: Template) -> None:
        if not template:
            return

        self.template = template
        self.children._clear()
        
        await self.mount(Static(template.name))
        
        if isinstance(template, AERender):
            for asset in template.assets:
                await self.mount(Container(
                    Static(asset.layer, classes="label"),
                    Input(asset.value, classes="text-input", name=asset.layer),
                    classes="input"
                ))
            await self.mount(Button("Render", variant="primary"))
            await self.mount(ProgressBar("Rendering..."))

    async def on_button_pressed(self, event: Button.Pressed):
        values = {n.name: n.value for n in self.query(Input).results()}
        self.query_one(Button).disabled = True
        self.query_one(ProgressBar).visible = True
        self.query_one(ProgressBar).reset()
        self.app.query_one("#sidebar").visible = False
        assert isinstance(self.template, AERender)
        self.template.update_data(values)
        code, msg = await self.template.do_render(progress_callback=self.query_one(ProgressBar).update_progress)
        if code != 0:
            await self.app.push_screen(ErrorMessage(msg))
        self.query_one(Button).disabled = False
        print(self.app.query_one("#sidebar"))
        self.app.query_one("#sidebar").visible = True
        await sleep(3)
        self.query_one(ProgressBar).visible = False

class AEApp(App):
    CSS_PATH = "app.css"

    selected_template: reactive[Template | None] = reactive(None)

    def on_mount(self):
        self.title = "DTV Nest"

    def compose(self) -> ComposeResult:
        self.temps = Template.get_all_instances()
        yield Header(show_clock=True)
        yield ListView(
            *[ListItem(Label(t.name)) for t in self.temps],
            id="sidebar"
        )
        yield TemplateView(id="main")
        yield Footer()

    def on_list_view_selected(self, _):
        index = self.query_one(ListView).index
        self.selected_template = self.temps[index]


if __name__ == "__main__":
    app = AEApp()
    refs = Template.get_all_instances()
    app.run()
