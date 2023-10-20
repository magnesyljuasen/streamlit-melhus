import time
from datetime import datetime
import streamlit as st


def time_loop():
    t = st.empty()
    while True:
        current_time = datetime.now()
        if current_time.second == 59 and current_time.minute % 5 == 0:
            formatted_time = current_time.strftime("%H:%M:%S")
            return formatted_time
        t.markdown(f'{current_time.strftime("%d-%m-%Y")} **{current_time.strftime("%H:%M:%S")}**')
        time.sleep(1)
        