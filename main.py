## Testing area using the "Odds API" endpoint

# Settings
testing = False # Processes data from local file if true
online = False # Adjusts for aws lambda
sprtList = ['soccer_epl','soccer_france_ligue_one','soccer_france_ligue_two','soccer_germany_bundesliga','soccer_italy_serie_a','soccer_portugal_primeira_liga','soccer_spain_la_liga']
threshold = 0.02 # % for which Opps are sent by email

# import libs
import requests
import json
import datetime
import smtplib
from email.message import EmailMessage

def lambda_handler(event, context):

    def main(sprt):
        # Setup
        API_KEY = 'df165f5d8ccc34893562307a790b3074'
        SPORT = sprt # use the sport_key from the /sports endpoint below, or use 'upcoming' to see the next 8 games across all sports
        REGIONS = 'eu' # uk | us | eu | au. Multiple can be specified if comma delimited
        MARKETS = 'h2h' # h2h | spreads | totals. Multiple can be specified if comma delimited
        ODDS_FORMAT = 'decimal' # decimal | american
        DATE_FORMAT = 'iso' # iso | unix
        EMAIL_ADDRESS = 'hugodrw.pythonemail@gmail.com'
        EMAIL_PASSWORD = 'wbklsrxfnebfaywm'

        # For examples of usage quota costs, see https://the-odds-api.com/liveapi/guides/v4/#usage-quota-costs



        ####### Helper functions  ########### 

        def runQuery(testing, API_KEY, SPORT, REGIONS, MARKETS, ODDS_FORMAT, DATE_FORMAT):
            # Runs query to odds API and saves to file 

            odds_response = requests.get(
                f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
                params={
                    'api_key': API_KEY,
                    'regions': REGIONS,
                    'markets': MARKETS,
                    'oddsFormat': ODDS_FORMAT,
                    'dateFormat': DATE_FORMAT,
                }
            )

            if odds_response.status_code != 200:
                print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')
                exit()
            else:
                # Check the usage quota
                print('Remaining requests', odds_response.headers['x-requests-remaining'])
                print('Used requests', odds_response.headers['x-requests-used'])
                output = 'Remaining requests ' + odds_response.headers['x-requests-remaining']
                output += '\n Used requests ' + odds_response.headers['x-requests-used']

                odds_json = odds_response.json()
                # Save to file
                if not testing and not online:
                    with open('json_data.json', 'w') as outfile:
                        json.dump(odds_json, outfile)

            return odds_json, output



        ####### Main Script  ########### 
        print(sprt)
        output = ''
        if not testing:
            odds_json, output = runQuery(testing, API_KEY, SPORT, REGIONS, MARKETS, ODDS_FORMAT, DATE_FORMAT)
        else:
            with open('json_data.json') as json_file:
                try:
                    odds_json = json.load(json_file)
                except:
                    print("Empty JSON file")
                    exit()


        # continue script
        print('Number of events:', len(odds_json))
        #print(json.dumps(odds_json, indent=4))

        # go through events and find highest and lowest values
        for event in odds_json:
            # define event
            gamedate = event["commence_time"]
            # check if game is live
            if datetime.datetime.strptime(gamedate,"%Y-%m-%dT%H:%M:%SZ") < datetime.datetime.utcnow():
                print('livegame')
                continue

            ht = event["home_team"]
            at = event["away_team"]
            # print('home team ' + ht)
            # print('away team ' + at)
            bks = event["bookmakers"]
            ht_prices = []
            at_prices = []
            draw_prices = []
            bk_names = []
            for bk in bks:
                bk_names.append(bk["title"])
                outcomes = bk["markets"][0]["outcomes"]
                ht_index = next((i for i, item in enumerate(outcomes) if item["name"] == ht), None)
                ht_prices.append((bk["markets"][0]["outcomes"][ht_index]["price"]))
                at_index = next((i for i, item in enumerate(outcomes) if item["name"] == at), None)
                at_prices.append((bk["markets"][0]["outcomes"][at_index]["price"]))
                draw_index = next((i for i, item in enumerate(outcomes) if item["name"] == 'Draw'), None)
                draw_prices.append((bk["markets"][0]["outcomes"][draw_index]["price"]))

            ht_max_index = max(range(len(ht_prices)), key=ht_prices.__getitem__)
            at_max_index = max(range(len(at_prices)), key=at_prices.__getitem__)
            draw_max_index = max(range(len(draw_prices)), key=draw_prices.__getitem__)

            ht_max_value = ht_prices[ht_max_index]
            ht_max_bk = bk_names[ht_max_index]
            at_max_value = at_prices[at_max_index]
            at_max_bk = bk_names[at_max_index]
            draw_max_value = draw_prices[draw_max_index]
            draw_max_bk = bk_names[draw_max_index]

            total_prob = 1/ht_max_value + 1/at_max_value + 1/draw_max_value
            interest = 1 - total_prob

            # print('ht_prices ')
            # print(ht_prices)
            # print(ht_max_value)
            # print('at_prices ')
            # print(at_prices)
            # print(at_max_value)
            # print('draw_prices ' )
            # print(draw_prices)
            # print(draw_max_value)
            # print(total_prob)
            print('no. bookies checked: ' + str(len(bks)))

            if interest > threshold :
                print('')
                print('opportunity:')
                print('date: '+ gamedate)
                print('no. bookies checked: ' + str(len(bks)))
                print('interest: ' + str(round((interest)*100,2)) +'%')
                print('home team: ' + ht)
                print('odds: ' + str(ht_max_value))
                print('stake: ' + str(round(100/ht_max_value,2)))
                print('bookie: ' + ht_max_bk)
                print('away team: ' + at)
                print('odds: ' + str(at_max_value))
                print('stake: ' + str(round(100/at_max_value,2)))
                print('bookie: ' + at_max_bk)
                print('draw: ')
                print('odds: ' + str(draw_max_value))
                print('stake: ' + str(round(100/draw_max_value,2)))
                print('bookie: ' + draw_max_bk)

                output += '\n\n opportunity: '
                output += '\ndate: '+ gamedate
                output += '\nno. bookies checked: ' + str(len(bks))
                output += '\n interest: ' + str(round((1 - total_prob)*100,2)) +'%'
                output += '\n home team: ' + ht
                output += '\n odds: ' + str(ht_max_value)
                output += '\n stake: ' + str(round(100/ht_max_value,2))
                output += '\n bookie: ' + ht_max_bk
                output += '\n away team: ' + at
                output += '\n odds: ' + str(at_max_value)
                output += '\n stake: ' + str(round(100/at_max_value,2))
                output += '\n bookie: ' + at_max_bk
                output += '\n draw: '
                output += '\n odds: ' + str(draw_max_value)
                output += '\n stake: ' + str(round(100/draw_max_value,2))
                output += '\n bookie: ' + draw_max_bk

        # Send results to email
        msg = EmailMessage()
        msg['Subject'] = 'SportsBot Update'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = 'hugodrw@icloud.com'

        msg.set_content(output)


        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)

    for sprt in sprtList:
        main(sprt)    

# Run function offline
if not online:
    lambda_handler('event','context')