from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class ConversationState(TypedDict, total=False):
    user_obj: object
    new_message: str
    stage: str
    response: str | None


def classify_message(state: ConversationState) -> ConversationState:
    message = state['new_message'].casefold()
    appointment_words = ('randevu', 'gelmek', 'görüşme', 'ziyaret', 'kayıt olmak', 'kaydol')
    rejection_words = ('istemiyorum', 'gerek yok', 'teşekkürler', 'sonra bakarım', 'hayır')

    if any(word in message for word in appointment_words):
        stage = 'appointment'
    elif any(word in message for word in rejection_words):
        stage = 'closing'
    else:
        stage = 'information'
    return {'stage': stage}


def route_stage(state: ConversationState) -> Literal['information', 'appointment', 'closing']:
    return state['stage']


def generate_information_response(state: ConversationState) -> ConversationState:
    return _generate_response(state, 'Bilgi ver; kısa ve açıklayıcı ol. Önce soruyu yanıtla, sonra başka sorusu olup olmadığını sor.')


def generate_appointment_response(state: ConversationState) -> ConversationState:
    return _generate_response(state, 'Randevu akışını uygula. Önce İncek-Alacaatlı konumunu ve uygun gün/saat seçeneklerini sun; onay alırsan veli ve sporcu bilgilerini sırayla iste.')


def generate_closing_response(state: ConversationState) -> ConversationState:
    return _generate_response(state, 'Kullanıcı randevuyu reddetti. Zorlama; 0506 480 20 24 iletişim numarasını paylaş, teşekkür et ve sohbeti nazikçe bitir.')


def _generate_response(state: ConversationState, instruction: str) -> ConversationState:
    from .views import get_gemini_messages

    response = get_gemini_messages(
        state['user_obj'],
        state['new_message'],
        additional_instruction=instruction,
    )
    return {'response': response}


def build_conversation_graph():
    graph = StateGraph(ConversationState)
    graph.add_node('classify', classify_message)
    graph.add_node('information', generate_information_response)
    graph.add_node('appointment', generate_appointment_response)
    graph.add_node('closing', generate_closing_response)
    graph.add_edge(START, 'classify')
    graph.add_conditional_edges('classify', route_stage)
    graph.add_edge('information', END)
    graph.add_edge('appointment', END)
    graph.add_edge('closing', END)
    return graph.compile()


conversation_graph = build_conversation_graph()


def generate_conversation_response(user_obj, new_message: str):
    result = conversation_graph.invoke({
        'user_obj': user_obj,
        'new_message': new_message,
    })
    return result.get('response')
