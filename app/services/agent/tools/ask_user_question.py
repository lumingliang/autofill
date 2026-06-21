"""
AskUserQuestion 工具 - 询问用户问题
"""
from typing import List

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.services.agent.tool_executor import format_tool_result


class QuestionOption(BaseModel):
    label: str = Field(description="The display text for this option that the user will see and select. Should be\nconcise (1-5 words) and clearly describe the choice.")
    description: str = Field(description="Explanation of what this option means or what will happen if chosen. Useful for\nproviding context about trade-offs or implications.")


class Question(BaseModel):
    header: str = Field(description='Very short label displayed as a chip/tag (max 12 chars). Examples: "Auth\nmethod", "Library", "Approach".')
    options: List[QuestionOption] = Field(min_length=2, max_length=4, description="The available choices for this question. Must have 2-4 options. Each option\nshould be a distinct, mutually exclusive choice (unless multiSelect is enabled).\nThere should be no 'Other' option, that will be provided automatically.")
    question: str = Field(description='The complete question to ask the user. Should be clear, specific, and end with a\nquestion mark. Example: "Which library should we use for date formatting?" If\nmultiSelect is true, phrase it accordingly, e.g. "Which features do you want to\nenable?"')
    multiSelect: bool = Field(default=False, description="Set to true to allow the user to select multiple options instead of just one.\nUse when choices are not mutually exclusive.")


class AskUserQuestionInput(BaseModel):
    questions: List[Question] = Field(min_length=1, max_length=4, description="Questions to ask the user (1-4 questions)")


async def execute_ask_user_question(questions: List[dict]) -> str:
    """执行 AskUserQuestion 工具 - 与 1.json 一致"""
    return format_tool_result("done", {
        "questions": questions,
        "status": "waiting_for_user"
    })


def get_ask_user_question_tool() -> BaseTool:
    return StructuredTool.from_function(
        name="AskUserQuestion",
        description="Use this tool when you need to ask the user questions during execution. \nThis allows you to: \n  1. Gather user preferences or requirements \n  2. Clarify ambiguous instructions \n  3. Get decisions on implementation choices as you work \n  4. Offer choices to the user about what direction to take. \nUsage notes: \n  - IMPORTANT: When the user explicitly invites discussion (e.g., \"discuss\", \"decide together\", \"let's talk about\", \"讨论一下\", \"你觉得呢\") AND the request has not yet converged to a specific action, use this tool proactively to structure the discussion into clear options before producing a final output.\n  - Users will always be able to select \"Other\" to provide custom text input\n  - Use multiSelect: true to allow multiple answers to be selected for a question\n  - If you recommend a specific option, make that the first option in the list and add \"(Recommended)\" at the end of the label \n",
        func=None,
        coroutine=execute_ask_user_question,
        args_schema=AskUserQuestionInput,
    )
