"""
core/ui_renderer.py
Registry-based Dynamic UI Renderer (ARCHITECTURAL EXEMPTION — "توضیح ۱")

NEW FILE. Does not modify app.py, modules/dashboard.py, or
core/ui_components.py — I have not seen those files, so this module is
self-contained and ready to be called from them, but the final wiring
("call render_dynamic_strategy_panel() from dashboard.py") still needs to
be done once those files are available.

Design:
  - No strategy-specific code lives here. Every strategy's parameters are
    rendered purely from the metadata `core.strategy_registry.list_dynamic_ui_metadata()`
    returns. Adding a 21st strategy requires zero changes to this file.
  - Only the project's allowed input widgets are used: st.selectbox,
    st.radio, st.checkbox. (st.slider / st.toggle remain forbidden.)
  - Every parameter gets a concise one-line label plus a st.popover("?")
    with a short help string — knowledge-on-demand without cluttering the
    main view.
  - `st.multiselect` is used only for the strategy picklist itself (not a
    per-parameter control), as a stand-in for the project's documented
    "checkbox_group" widget, whose exact API lives in core/ui_components.py
    which I have not seen. Swap this one line for the project's real
    checkbox_group once that file is available — nothing else depends on it.
"""

import streamlit as st

from core.strategy_registry import list_dynamic_ui_metadata


_WIDGET_RENDERERS = {
    "selectbox": lambda field, key: st.selectbox(
        field["label"], field["options"],
        index=field["options"].index(field["default"]) if field["default"] in field["options"] else 0,
        label_visibility="collapsed", key=key,
    ),
    "radio": lambda field, key: st.radio(
        field["label"], field["options"],
        index=field["options"].index(field["default"]) if field["default"] in field["options"] else 0,
        horizontal=True, label_visibility="collapsed", key=key,
    ),
    "checkbox": lambda field, key: st.checkbox(
        field["label"], value=bool(field["default"]),
        label_visibility="collapsed", key=key,
    ),
}


def render_param_field(strategy_key: str, field: dict):
    """Renders one parameter: concise label + '?' popover + its widget."""
    widget_key = f"{strategy_key}__{field['key']}"

    label_col, help_col = st.columns([6, 1])
    with label_col:
        st.markdown(f"<span style='font-size:0.85rem'>{field['label']}</span>", unsafe_allow_html=True)
    with help_col:
        with st.popover("?"):
            st.caption(field.get("help", ""))

    renderer = _WIDGET_RENDERERS.get(field["widget"])
    if renderer is None:
        # Unknown widget type in the schema — surfaced, not silently guessed.
        st.caption(f"⚠️ unsupported widget type: {field['widget']}")
        return field.get("default")

    return renderer(field, widget_key)


def render_strategy_params(strategy_key: str, params_schema: list) -> dict:
    """Renders every field of one strategy's schema, returns {key: value}."""
    selections = {}
    for field in params_schema:
        selections[field["key"]] = render_param_field(strategy_key, field)
    return selections


def render_dynamic_strategy_panel() -> dict:
    """
    Auto-detects every registered strategy (via the registry, not a
    hardcoded list) and renders its parameter block if the user enables it.

    Returns: {strategy_key: {param_key: selected_value}} for every strategy
    the user turned on — ready to pass as inputs["ui_params"] into that
    strategy's Adapter.run().
    """
    all_meta = list_dynamic_ui_metadata()

    enabled_labels = st.multiselect(
        "Strategies",
        [meta["label"] for meta in all_meta],
        label_visibility="visible",
    )

    ui_selections: dict = {}
    for meta in all_meta:
        if meta["label"] not in enabled_labels:
            continue
        if not meta["params_schema"]:
            # Strategy has no Dynamic UI schema yet (e.g. MC/PX pre-exemption) — skip silently.
            continue
        with st.expander(meta["label"], expanded=False):
            ui_selections[meta["key"]] = render_strategy_params(meta["key"], meta["params_schema"])

    return ui_selections
