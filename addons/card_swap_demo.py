import json
from typing import Any

import mitmproxy.http

from addons.base import DokkanBaseAddon

"""
    CardSwapDemo addon
    ==================
    
    Demo/template addon. Replaces oldest (first) card with LR Teq Broly.
    
"""


class CardSwapDemo(DokkanBaseAddon):
    replaced_cards = {}

    def filter_request(self, http: mitmproxy.http.HTTPFlow) -> bool:
        """
            https://1c.ishin-prod.aktsk.jp/resources/login?awakening_items=true&budokai=true&card_tags=true&cards=true
           [Proto] [       Host         ][      Path     ][                         Query                            ]

           There's two ways Dokkan sends us card info, the /resources/login path and /cards path.
           We also only care about the response, so make sure it's available.
        """
        return ("cards" in http.request.query or http.request.path == "/cards") and http.response is not None

    def replace_card(self, card: Any, new_card_id: int) -> Any:
        """
            card['id'] link the card to the user
            card['card_id'] links the card to the database

            We save the original version of the card in case we want to reverse the change later.

            We return the edited card
        """
        print(f'[CARD SWAP] Changing {card["id"]} from {card["card_id"]} to {new_card_id}')
        self.replaced_cards[card['id']] = card
        card['card_id'] = new_card_id
        return card

    def intercept_response(self, http: mitmproxy.http.HTTPFlow):
        # Each card list intercept we clear the list of replaced cards since we're doing it all over again
        self.replaced_cards.clear()
        # Decode the json body
        json_data = json.loads(http.response.text)
        # Replace the card
        json_data['cards'][0] = self.replace_card(json_data['cards'][0], 1016871)
        # Replace the original server data with the edited version
        http.response.text = json.dumps(json_data)
