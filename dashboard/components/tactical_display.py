"""Plotly tactical display — scatter plot with aircraft, missiles, and radar rings."""

from __future__ import annotations

from typing import Dict, List

import plotly.graph_objects as go


def make_tactical_figure(snapshot: Dict, scenario_name: str) -> go.Figure:
    """Create a Plotly tactical picture from a state snapshot."""
    fig = go.Figure()

    # -- Aircraft --
    ac_list = snapshot.get("aircraft", [])
    for team, color, symbol in [
        ("Blue", "rgb(0,212,255)", "triangle-right"),
        ("Red", "rgb(255,59,59)", "triangle-left"),
    ]:
        alive = [a for a in ac_list if a["team"] == team and a["is_alive"]]
        xs = [a["x_km"] for a in alive]
        ys = [a["y_km"] for a in alive]
        ids = [a["aircraft_id"] for a in alive]

        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text",
            marker={"symbol": symbol, "size": 14, "color": color,
                    "line": {"width": 1, "color": "white"}},
            text=ids, textposition="top center",
            name=f"{team} Force",
        ))

    # -- Missiles --
    missiles = snapshot.get("missiles", [])
    if missiles:
        mx = [m["x_km"] for m in missiles]
        my = [m["y_km"] for m in missiles]
        m_colors = ["white" if "Blue" in m["owner_id"] else "orange" for m in missiles]
        fig.add_trace(go.Scatter(
            x=mx, y=my, mode="markers",
            marker={"size": 6, "color": m_colors},
            name="Missiles",
        ))

    t_sec = snapshot.get("t_sec", 0)
    fig.update_layout(
        title={"text": f"⚔ {scenario_name} — t = {t_sec:.1f}s", "font": {"size": 18, "color": "#00D4FF"}},
        template="plotly_dark",
        paper_bgcolor="#080C14",
        plot_bgcolor="#0D1321",
        height=650,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        xaxis={"title": "x (km)", "zeroline": False, "gridcolor": "rgba(255,255,255,0.05)"},
        yaxis={"title": "y (km)", "zeroline": False, "scaleanchor": "x", "scaleratio": 1,
                   "gridcolor": "rgba(255,255,255,0.05)"},
        legend={"orientation": "h", "x": 1, "xanchor": "right", "y": 1.02},
    )
    return fig


def make_animated_tactical_figure(history: List[Dict], scenario_name: str) -> go.Figure:
    """Create a Plotly figure with animation frames for the whole history."""
    if not history:
        return go.Figure()

    # Initial frame
    fig = make_tactical_figure(history[0], scenario_name)
    
    # Add frames
    frames = []
    for i, snapshot in enumerate(history):
        # We need to recreate the traces for each frame
        frame_data = []
        
        # Aircraft traces
        ac_list = snapshot.get("aircraft", [])
        for team, color, symbol in [
            ("Blue", "rgb(0,212,255)", "triangle-right"),
            ("Red", "rgb(255,59,59)", "triangle-left"),
        ]:
            alive = [a for a in ac_list if a["team"] == team and a["is_alive"]]
            xs = [a["x_km"] for a in alive]
            ys = [a["y_km"] for a in alive]
            ids = [a["aircraft_id"] for a in alive]
            
            frame_data.append(go.Scatter(
                x=xs, y=ys, mode="markers+text",
                marker={"symbol": symbol, "size": 14, "color": color},
                text=ids, textposition="top center",
                name=f"{team} Force"
            ))
            
        # Missile traces
        missiles = snapshot.get("missiles", [])
        mx = [m["x_km"] for m in missiles]
        my = [m["y_km"] for m in missiles]
        m_colors = ["white" if "Blue" in m["owner_id"] else "orange" for m in missiles]
        frame_data.append(go.Scatter(
            x=mx, y=my, mode="markers",
            marker={"size": 6, "color": m_colors},
            name="Missiles"
        ))
        
        frames.append(go.Frame(data=frame_data, name=f"fr{i}"))

    fig.frames = frames
    
    # Add simulation controls to layout
    fig.update_layout(
        updatemenus=[{"type": "buttons",
            "showactive": False,
            "buttons": [{"label": "▶ Play",
                "method": "animate",
                "args": [None, {"frame": {"duration": 100, "redraw": True}, "fromcurrent": True}]
            }, {"label": "⏸ Pause",
                "method": "animate",
                "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]
            }]
        }],
        sliders=[{"steps": [{"method": "animate",
                "args": [[f"fr{i}"], {"mode": "immediate", "frame": {"duration": 0, "redraw": True}}],
                "label": f"{history[i]['t_sec']:.0f}s"
            } for i in range(0, len(history), max(1, len(history)//20))],
            "transition": {"duration": 0},
            "x": 0, "y": 0, "currentvalue": {"font": {"size": 12}, "prefix": "Time: ", "visible": True, "xanchor": "right"}
        }]
    )
    
    return fig
