from fastapi import FastAPI
from fastapi.responses import JSONResponse

from vigilant.common.exceptions import VigilantException
from vigilant.run import main as run

app = FastAPI()


@app.post("/sync-finances")
def sync_finances() -> str:
    """Start process for collecting finance data and load it into a google
    spreadsheet

    Returns:
        str: Finished process status message
    """
    try:
        run()
        return "Ok"
    except VigilantException as e:
        return JSONResponse(status_code=500, content={"details": str(e)})
