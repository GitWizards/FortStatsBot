import json
from datetime import timedelta
import requests


def prepare_result_msg(username, account_type="epic", time_window="lifetime", match_type="overall") -> str:
    r = requests.get("https://fortnite-api.com/v1/stats/br/v2"
                     f"?name={username}"
                     f"&accountType={account_type}"
                     f"&timeWindow={time_window}")
    data = json.loads(r.text)

    if data['status'] != 200:
        rv = f"User *{username}* not found on *{account_type.capitalize()}* platform! 🤷🏼‍♂️🔍"
    else:
        rv = f"🎖 *Battle pass*: {data['data']['battlePass']['level']}\n\n"

        # Shortcut
        stats = data['data']['stats']['all'][match_type]

        rv += f"⚔️  *{match_type.capitalize()}* ⚔️\n\n"

        if stats is not None:
            rv += f"📈 *Score*: {stats['score']}\n"

            if match_type == 'overall':
                rv += f"🥇 *Wins*: {stats['wins']}\n"
                rv += f"🥈 *Top 3*: {stats['top3']}\n"
                rv += f"🥉 *Top 10*: {stats['top10']}\n\n"
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

            rv += f"🏆 *Win rate*: {stats['winRate']}\n"
            rv += f"▶️  *Matches*: {stats['matches']}\n\n"

            rv += f"💪🏻 *Kills*: {stats['kills']}\n"
            rv += f"💀 *Deaths*: {stats['deaths']}\n"
            rv += f"🧑‍🚀 *K/D ratio*: {stats['kd']}\n\n"

            rv += f"🕒 *Time played*: {str(timedelta(minutes=stats['minutesPlayed']))[:-3]}"
        else:
            rv += "*No data found for this game type!*"

    return rv
