from .taxifishka_handlers import *
from .taxifishka_const import *
from .taxifishka_utils import *


def TAXIFISHKA_COMMANDS(message, client):
    handlers = {
        'new': register_handler,
        'force_new': force_register_handler,
        'choose_city': choose_city_handler,
        'get_phone': get_phone_handler,
        'wait_order': order_handler,
        'get_address': get_address_handler,
        'confirm_address': confirm_address_handler,
        'force_order': force_order_handler,
        'confirm_order': confirm_order_handler,
        'choose_attr': choose_attr_handler,
        'get_comment': get_comment_handler,
        'process_order': process_order_handler,
        'confirm_cancel': confirm_cancel_handler,
        'wait_menu_command': wait_menu_command_handler,
        'get_history': get_history_handler,
        'get_family_member': get_family_member_handler,
        'get_family_member_phone': get_family_member_phone_handler,
        'confirm_family_member': confirm_family_member_handler,
        'get_family_member_name': get_family_member_name_handler,
        'get_family_member_action': get_family_member_action_handler,
        'confirm_delete_family_member': confirm_delete_family_member_handler,
        'rename_family_member': rename_family_member_handler,
        'choose_profile_action': choose_profile_action_handler,
        'get_review': get_review_handler,
    }
    message = delete_emoji(message, client)
    if message.get('text', '') == TAXIFISHKA_END_TOKEN:
        return end_order_handler(message, client)
    if message.get('text', '') == TAXIFISHKA_SEND_TOKEN:
        return send_order_handler(message, client)
    if message.get('text', '') == TAXIFISHKA_PRICE_TOKEN:
        return price_order_handler(message, client)
    if message.get('text', '') == TAXIFISHKA_CHECK_TOKEN:
        return observe_orders()
    handler = handlers.get(client.state)
    if not handler:
        return ('Ваша учетная запись находится в некорректном состоянии, обратитесь к администратору rumyancevandr@yandex.ru',
                [])
    return handler(message, client)
