# -*- coding: iso8859-15 -*-
import os
import sys

from src.global_config import logger

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)


from global_config import ScopedSession
from event_archive.db_models.event import EventModel
from event_archive.systems.system import reacts_to_anything


@reacts_to_anything
def record_event(topic, payload, timestamp):
    if topic.endswith("statistics"):
        return  # Statistic should be in realtime, record it just make our event archive heavier
    session = None
    try:
        with ScopedSession() as session:
            event = EventModel(topic=topic, payload=payload, mqtt_timestamp=timestamp)
            session.add(event)
            session.flush()
    except Exception as error:
        logger.error(error)
    finally:
        if session is not None:
            session.close()
