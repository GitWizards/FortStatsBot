import json
from datetime import timedelta
from json.decoder import JSONDecodeError

import requests


class MessageConverter:
    def __init__(self):
        self.season_icon = self.get_season_icon()

        self.__human_to_machine_strings = {
            '🔲 Epic': 'epic',
            '🟦 PSN': 'psn',
            '🟩 Xbox': 'xbl',
            '🍃 Lifetime': 'lifetime',
            f'{self.season_icon} Season': 'season',
            '🔢 Everything': 'overall',
            '1️⃣ Solo': 'solo',
            '2️⃣ Duo': 'duo',
            '3️⃣ Trio': 'trio',
            '4️⃣ Squad': 'squad',
            '🔐 Limited modes': 'ltm',
        }

        self.__machine_to_human_strings = {
            v: k for k, v in self.__human_to_machine_strings.items()}

    def get_season_icon(self) -> str:
        try:
            return json.loads(requests.get('https://pastebin.com/raw/HNxPB0zp').text)['time_window']
        except JSONDecodeError:
            return "❌"

    def human_to_machine(self, human_str) -> str:
        if human_str in self.__human_to_machine_strings.keys():
            rv = self.__human_to_machine_strings[human_str]
        else:
            rv = "Undefined"
        return rv

    def machine_to_human(self, machine_str) -> str:
        if machine_str in self.__machine_to_human_strings.keys():
            rv = self.__machine_to_human_strings[machine_str]
        else:
            rv = "Undefined"
        return rv


def prepare_result_msg(username, account_type="epic", time_window="lifetime", match_type="overall", api_key=None) -> str:
    data = json.loads(
        requests.get(
            "https://fortnite-api.com/v1/stats/br/v2"
            f"?name={username}&accountType={account_type}&timeWindow={time_window}",
            headers={"Authorization": api_key}
        ).text
    )

    # Sanitize input
    username = username.replace('_', '\_').capitalize()

    if data['status'] != 200:
        rv = f"User *{username}* not found on *{account_type.upper()}* platform! 🤷🏼‍♂️🔍"
    else:
        rv = f"👤 *Username*: {username}\n"
        rv += f"⭐️ *Battle pass*: {data['data']['battlePass']['level']}\n\n"

        # Shortcut
        stats = data['data']['stats']['all'][match_type]

        rv += f"⚔️  *{match_type.capitalize()}* ⚔️\n\n"

        if stats is not None:
            rv += f"📈 *Score*: {stats['score']}\n"

            if match_type == 'overall':
                rv += f"👑 *Wins*: {stats['wins']}\n"
                rv += f"🥇 *Top 3*: {stats['top3']}\n"
                rv += f"🥈 *Top 5*: {stats['top5']}\n"
                rv += f"🥉 *Top 6*: {stats['top6']}\n"
                rv += f"🎖 *Top 10*: {stats['top10']}\n"
                rv += f"🎖 *Top 12*: {stats['top12']}\n"
                rv += f"🎖 *Top 25*: {stats['top25']}\n\n"
            elif match_type == 'solo':
                rv += f"🥇 *Wins*: {stats['wins']}\n"
                rv += f"🥈 *Top 10*: {stats['top10']}\n"
                rv += f"🥉 *Top 25*: {stats['top25']}\n\n"
            elif match_type == 'duo':
                rv += f"🥇 *Wins*: {stats['wins']}\n"
                rv += f"🥈 *Top 5*: {stats['top5']}\n"
                rv += f"🥉 *Top 12*: {stats['top12']}\n\n"
            elif match_type == 'trio':
                rv += f"🥇 *Wins*: {stats['wins']}\n"
                rv += f"🥈 *Top 3*: {stats['top3']}\n"
                rv += f"🥉 *Top 6*: {stats['top6']}\n\n"
            elif match_type == 'squad':
                rv += f"🥇 *Wins*: {stats['wins']}\n"
                rv += f"🥈 *Top 3*: {stats['top3']}\n"
                rv += f"🥉 *Top 6*: {stats['top6']}\n\n"
            elif match_type == 'ltm':
                rv += f"🥇 *Wins*: {stats['wins']}\n"

            rv += f"🏆 *Win rate*: {stats['winRate']}%\n"
            rv += f"▶️  *Matches*: {stats['matches']}\n\n"

            rv += f"💪🏻 *Kills*: {stats['kills']}\n"
            rv += f"💀 *Deaths*: {stats['deaths']}\n"
            rv += f"🧑‍🚀 *K/D ratio*: {stats['kd']}\n\n"

            rv += f"🕒 *Time played*: {str(timedelta(minutes=stats['minutesPlayed']))[:-3]}"
        else:
            rv += "*No data found for this game type!*"

    return rv
