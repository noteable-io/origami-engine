"""A Papermill engine that combines Dagstermill and Noteable."""
import nbformat
from dagstermill.compat import ExecutionError

from ..engine import NoteableEngine


class NoteableDagstermillEngine(NoteableEngine):
    async def papermill_execute_cells(self):
        try:
            # Run the Noteable execute cells
            await super().papermill_execute_cells()
        finally:
            # After execution or on error, run the Dagstermill teardown
            new_cell = nbformat.v4.new_code_cell(
                source="import dagstermill as __dm_dagstermill\n__dm_dagstermill._teardown()\n"
            )
            new_cell.metadata["tags"] = ["injected-teardown"]
            new_cell.metadata["papermill"] = {
                "exception": None,
                "start_time": None,
                "end_time": None,
                "duration": None,
                "status": self.nb_man.PENDING,
            }
            index = len(self.nb_man.nb.cells)
            after_id = self.nb_man.nb.cells[-1]["id"]

            self.nb_man.nb.cells = self.nb_man.nb.cells + [new_cell]
            await self.km.client.add_cell(self.file, cell=new_cell, after_id=after_id)

            try:
                self.nb_man.cell_start(new_cell, index)
                await self.async_execute_cell(new_cell, index)
            except ExecutionError as ex:
                self.nb_man.cell_exception(self.nb.cells[index], cell_index=index, exception=ex)
            finally:
                self.nb_man.cell_complete(self.nb.cells[index], cell_index=index)
