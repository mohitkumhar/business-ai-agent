from intents.general_information_graph.subgraph import general_information_graph_workflow


def handle(text, intent_meta):
    initial_state = {"user_query": text}
    config = {"configurable": {"thread_id": "default-thread"}}

    final_output = None
    for result in general_information_graph_workflow.stream(
        initial_state,
        config=config
    ):
        final_output = result

    return final_output
