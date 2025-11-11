from __future__ import annotations

from langgraph.graph import END, StateGraph

from .nodes import (
    NodeContext,
    finalize_node,
    make_book_flight_node,
    make_book_hotel_node,
    make_flight_search_node,
    make_hotel_search_node,
    make_issue_ticket_node,
    make_parse_intent_node,
    make_reprice_hold_node,
    make_select_offers_node,
    traveler_confirm_node,
    present_options_node,
)
from .state import ConversationState


def build_graph(ctx: NodeContext):
    graph = StateGraph(ConversationState)
    graph.add_node("parse_intent", make_parse_intent_node(ctx))
    graph.add_node("flight_search", make_flight_search_node(ctx))
    graph.add_node("hotel_search", make_hotel_search_node(ctx))
    graph.add_node("present_options", present_options_node)
    graph.add_node("select_offers", make_select_offers_node())
    graph.add_node("reprice_hold", make_reprice_hold_node(ctx))
    graph.add_node("traveler_confirm", traveler_confirm_node)
    graph.add_node("book_flight", make_book_flight_node(ctx))
    graph.add_node("issue_ticket", make_issue_ticket_node(ctx))
    graph.add_node("book_hotel", make_book_hotel_node(ctx))
    graph.add_node("finalize", finalize_node)

    def route_from_parse(state: ConversationState):
        entities = state.entities
        if entities and entities.is_confirm:
            return "traveler_confirm"
        if entities and (entities.selection_flights or entities.selection_hotels):
            return "select_offers"
        if entities and (entities.want_flights or entities.want_hotels):
            return "flight_search"
        return "present_options"

    graph.set_entry_point("parse_intent")
    graph.add_conditional_edges(
        "parse_intent",
        route_from_parse,
        {
            "traveler_confirm": "traveler_confirm",
            "select_offers": "select_offers",
            "flight_search": "flight_search",
            "present_options": "present_options",
        },
    )
    graph.add_edge("flight_search", "hotel_search")
    graph.add_edge("hotel_search", "present_options")
    graph.add_edge("select_offers", "reprice_hold")
    graph.add_edge("reprice_hold", END)

    def guard_after_confirm(state: ConversationState):
        if state.entities and state.entities.is_confirm and not state.last_error:
            return "book_flight"
        return END

    graph.add_conditional_edges(
        "traveler_confirm",
        guard_after_confirm,
        {
            "book_flight": "book_flight",
            END: END,
        },
    )
    graph.add_edge("book_flight", "issue_ticket")
    graph.add_edge("issue_ticket", "book_hotel")
    graph.add_edge("book_hotel", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()
