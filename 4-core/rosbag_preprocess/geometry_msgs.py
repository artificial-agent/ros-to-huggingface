#!/usr/bin/env python3
###############################################################################################################
"""
artificial-agent
09-25-2024
"""
"""
geometry_msgs.py
"""
###############################################################################################################


###############################################################################################################
# External imports
from genpy import Message, Time
import numpy as np
###############################################################################################################


###############################################################################################################
def process_twist(msg: Message, time_stamp: Time, extra_options: dict=None) -> dict:
    vx = msg.linear.x
    vy = msg.linear.y
    vz = msg.linear.z

    wx = msg.angular.x
    wy = msg.angular.y
    wz = msg.angular.z

    return {
        "stamp": time_stamp,

        "vx": vx,
        "vy": vy,
        "vz": vz,

        "wx": wx,
        "wy": wy,
        "wz": wz,
    }


###############################################################################################################

# EOF