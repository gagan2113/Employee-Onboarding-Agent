from langgraph.graph import StateGraph, END
from workflows.state import OnboardingState, OnboardingStep
from workflows.nodes import OnboardingNodes
from typing import Dict, Any

def create_onboarding_workflow(llm, slack_client, db_session):
    """Create the LangGraph workflow for onboarding"""
    
    # Initialize nodes
    nodes = OnboardingNodes(llm, slack_client, db_session)
    
    # Create the graph
    workflow = StateGraph(OnboardingState)
    
    # Add nodes
    workflow.add_node("welcome", nodes.welcome_node)
    workflow.add_node("collect_info", nodes.collect_info_node)
    workflow.add_node("share_policies", nodes.share_policies_node)
    workflow.add_node("tool_access", nodes.tool_access_node)
    workflow.add_node("culture_intro", nodes.culture_intro_node)
    workflow.add_node("assign_mentor", nodes.assign_mentor_node)
    workflow.add_node("track_progress", nodes.track_progress_node)
    workflow.add_node("collect_feedback", nodes.collect_feedback_node)
    workflow.add_node("completion", nodes.completion_node)
    
    # Define edges (transitions)
    workflow.add_edge("welcome", "collect_info")
    workflow.add_edge("collect_info", "share_policies")
    workflow.add_edge("share_policies", "tool_access")
    workflow.add_edge("tool_access", "culture_intro")
    workflow.add_edge("culture_intro", "assign_mentor")
    workflow.add_edge("assign_mentor", "track_progress")
    workflow.add_edge("track_progress", "collect_feedback")
    workflow.add_edge("collect_feedback", "completion")
    workflow.add_edge("completion", END)
    
    # Set entry point
    workflow.set_entry_point("welcome")
    
    return workflow.compile()

def should_continue_onboarding(state: OnboardingState) -> str:
    """Determine if onboarding should continue or end"""
    if state.current_step == OnboardingStep.COMPLETION:
        return END
    return state.current_step.value

def route_to_next_step(state: OnboardingState) -> str:
    """Route to the next appropriate step based on current state"""
    step_order = [
        OnboardingStep.WELCOME,
        OnboardingStep.COLLECT_INFO,
        OnboardingStep.SHARE_POLICIES,
        OnboardingStep.TOOL_ACCESS,
        OnboardingStep.CULTURE_INTRO,
        OnboardingStep.ASSIGN_MENTOR,
        OnboardingStep.TRACK_PROGRESS,
        OnboardingStep.COLLECT_FEEDBACK,
        OnboardingStep.COMPLETION
    ]
    
    current_index = step_order.index(state.current_step)
    
    if current_index < len(step_order) - 1:
        return step_order[current_index + 1].value
    else:
        return END
