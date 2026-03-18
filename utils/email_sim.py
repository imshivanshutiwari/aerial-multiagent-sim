"""Simulates sending email notifications with simulation results."""

import os
from datetime import datetime
from email.message import EmailMessage

_OUTBOX_DIR = "mail_outbox"

def send_simulation_report(result) -> str:
    """
    Generates an .eml file summarizing the simulation result.
    
    Args:
        result (SimulationResult): The end-of-sim result object.
        
    Returns:
        str: Path to the generated .eml file.
    """
    if not os.path.exists(_OUTBOX_DIR):
        os.makedirs(_OUTBOX_DIR)

    msg = EmailMessage()
    msg['Subject'] = f"BVR Combat Simulation Report - {result.scenario_name}"
    msg['From'] = "sim_engine@bvr_combat.io"
    msg['To'] = "commander@bvr_combat.io"
    msg['Date'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

    content = f"""
    BVR Combat Simulation completed successfully.
    
    Scenario Summary:
    -----------------
    Name: {result.scenario_name}
    Duration: {result.duration_sec:.1f} seconds
    
    Casualties:
    -----------
    Blue Losses: {result.blue_losses}
    Red Losses: {result.red_losses}
    Kill Ratio (Blue / Red): {result.kill_ratio:.2f}
    
    Engagement Statistics:
    ----------------------
    Blue Missiles Fired: {result.missiles_fired_blue}
    Red Missiles Fired: {result.missiles_fired_red}
    Total Events Logged: {len(result.event_log)}
    
    Please review the Streamlit dashboard for detailed replay analysis.
    
    -- BVR Combat Automated System
    """
    
    msg.set_content(content)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.eml"
    file_path = os.path.join(_OUTBOX_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(bytes(msg))

    print(f"\n[Email System] Simulation report saved locally: {file_path}")
    return file_path
