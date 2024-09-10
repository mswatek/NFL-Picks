import streamlit as st
import pandas as pd
import gspread
import numpy as np
import altair as alt
import IPython
import plotly.express as px
import seaborn as sns

from google.oauth2.service_account import Credentials

########################### TO DO LIST #################################
#### more call-outs in various spots
#### fix team scatterplots - dashed vertical and horizontal lines
#### for comparison call-outs, need to filter out current season
#### formatting on tallies table

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
]

skey = st.secrets["gcp_service_account"]
credentials = Credentials.from_service_account_info(
    skey,
    scopes=scopes,
)
client = gspread.authorize(credentials)

url = st.secrets["private_gsheets_url"]

# Perform SQL query on the Google Sheet.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
# @st.cache_data(ttl=600)

st.set_page_config(page_title="NFL Picks")
st.title("NFL Picks")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Picks", "Over/Under","Teams", "Tallies", "Full History"])

### bring in picks tab
sheet_name="Picks"
sh = client.open_by_url(url)
df_picks = pd.DataFrame(sh.worksheet(sheet_name).get_all_records())

filter = df_picks["Mat Result"] != ""
df_picks_year1 = pd.DataFrame(df_picks[filter]).reset_index()

df_picks_year1 = pd.melt(df_picks_year1, id_vars=['Year'], value_vars=['Mat Result','Dad Result']).reset_index()

conditions = [df_picks_year1.value =='W', df_picks_year1.value =='L', df_picks_year1.value =='T']
choices = [1, 0, 0.5]
df_picks_year1['Wins'] = np.select(conditions, choices)

df_picks_year2 =df_picks_year1.groupby(['Year','variable'])['Wins'].agg([('Games','size'), ('Win_Total','sum')]).reset_index()
df_picks_year2['Pct'] = df_picks_year2['Win_Total'].div(df_picks_year2['Games'], axis=0)

df_picks_year2 = df_picks_year2.rename(columns={'variable': 'Participant', 'Win_Total': 'Wins', 'Pct': 'Win Percentage'})
df_picks_year2['Participant'] = df_picks_year2['Participant'].astype('category')
df_picks_year2['Participant'] = df_picks_year2['Participant'].cat.rename_categories({'Mat Result': 'Mat', 'Dad Result': 'Dave'})

win_pct = alt.Chart(df_picks_year2).mark_bar().encode(
x=alt.X('Participant:O', title=None),
y='Win Percentage:Q',
color='Participant:N',
column='Year:N'
).properties(title='Win Percentage by Year')

### weekly cumulative picks

filter = df_picks["Mat Result"] != ""
df_picks1 = pd.DataFrame(df_picks[filter])
df_picks_week1 = pd.melt(df_picks1, id_vars=['Year','Week'], value_vars=['Mat Result','Dad Result']).reset_index()


conditions = [df_picks_week1.value =='W', df_picks_week1.value =='L', df_picks_week1.value =='T']
choices = [1, 0, 0.5]
df_picks_week1['Wins'] = np.select(conditions, choices)
df_picks_week12 = df_picks_week1.groupby(['Year','Week','variable'])['Wins'].agg([('Games','size'), ('Win_Total','sum')]).reset_index()
df_picks_week2 = df_picks_week1.groupby(['Year','Week','variable'])['Wins'].agg([('Games','size'), ('Win_Total','sum')]).groupby(level=[0,2]).cumsum().reset_index()
df_picks_week2['Pct_Cum'] = df_picks_week2['Win_Total'].div(df_picks_week2['Games'], axis=0)

df_picks_week13 = pd.DataFrame(df_picks_week12)
df_picks_week13['Year'] = df_picks_week13['Year'].astype(str)
df_picks_week13['Pct'] = df_picks_week13['Win_Total'].div(df_picks_week13['Games'], axis=0)

df_picks_week3 = pd.DataFrame(df_picks_week2)
#df_picks_week3['Year'] = df_picks_week3['Year'].astype(str)

df_picks_week3 = df_picks_week3.rename(columns={'variable': 'Participant', 'Win_Total': 'Wins', 'Pct_Cum': 'Cumulative Win Percentage'})
df_picks_week3['Participant'] = df_picks_week3['Participant'].astype('category')
df_picks_week3['Participant'] = df_picks_week3['Participant'].cat.rename_categories({'Mat Result': 'Mat', 'Dad Result': 'Dave'})

weekly_pct = px.line(df_picks_week3, x="Week", y="Cumulative Win Percentage", color='Year',line_dash='Participant',title="Cumulative Win Percentage by Year")

### current week's picks

filter = df_picks["Mat Pick"] != ""
df_picks_current1 = pd.DataFrame(df_picks[filter])


current_year = max(df_picks_current1.Year)
df_picks_current2 = pd.DataFrame(df_picks_current1.loc[np.where(df_picks_current1["Year"]==current_year)]).reset_index(drop=True)

current_week = max(df_picks_current2.Week)

df_picks_current = pd.DataFrame(df_picks_current2.loc[np.where(df_picks_current2["Week"]==current_week)]).reset_index(drop=True)
remaining_count = df_picks_current[df_picks_current["Mat Result"] ==""].shape[0]

df_picks_different = df_picks_current[df_picks_current['Mat Pick'] != df_picks_current['Dad Pick']] 
different_count = df_picks_different.shape[0]

df_results_current = pd.DataFrame(df_picks_year2.loc[np.where(df_picks_year2["Year"]==current_year)]).reset_index(drop=True)
df_results_current['Year'] = df_results_current['Year'].astype('string')

df_results_current_week1 = pd.DataFrame(df_picks_week3.loc[np.where(df_picks_week3["Year"]==current_year)]).reset_index()
current_results_week = max(df_results_current_week1.Week)
df_results_current_week = pd.DataFrame(df_results_current_week1.loc[np.where(df_results_current_week1["Week"]==current_results_week)]).reset_index()


df_results_current_Mat = pd.DataFrame(df_results_current.loc[np.where(df_results_current["Participant"]=="Mat")]).reset_index(drop=True)


df_results_current_week_Mat = pd.DataFrame(df_results_current_week.loc[np.where(df_results_current_week["Participant"]=="Mat")]).reset_index(drop=True)

week_games = df_results_current_week_Mat.iloc[0]['Games']

Mat_Wins = df_results_current_Mat.iloc[0]['Wins']
Mat_Losses = df_results_current_Mat.iloc[0]['Games'] - df_results_current_Mat.iloc[0]['Wins']
Mat_Pct = round(df_results_current_Mat.iloc[0]['Win Percentage'],3)

df_results_current_Dad = pd.DataFrame(df_results_current.loc[np.where(df_results_current["Participant"]=="Dave")]).reset_index()

Dad_Wins = df_results_current_Dad.iloc[0]['Wins']
Dad_Losses = df_results_current_Dad.iloc[0]['Games'] - df_results_current_Dad.iloc[0]['Wins']
Dad_Pct = round(df_results_current_Dad.iloc[0]['Win Percentage'],3)

diff = abs(Mat_Wins-Dad_Wins)
if diff>1:
   game_lead='games'
else:
   game_lead='game'

if Dad_Wins>Mat_Wins:
   picks_text = "Through {games} total games, Dave is ahead of Mat by {difference} {margin}. Dave's record is {wins_dad}-{losses_dad} ({pct_dad}) and Mat's is {wins_mat}-{losses_mat} ({pct_mat})." \
   .format(games=week_games, difference=format(Dad_Wins-Mat_Wins,',.0f'), margin=game_lead,wins_dad=Dad_Wins,losses_dad=Dad_Losses,pct_dad=Dad_Pct,wins_mat=Mat_Wins,losses_mat=Mat_Losses,pct_mat=Mat_Pct)
elif Dad_Wins<Mat_Wins:
   picks_text = "Through {games} total games, Mat leads Dave by {difference} {margin}. Mat's record is {wins_mat}-{losses_mat} ({pct_mat}) and Dave's is {wins_dad}-{losses_dad} ({pct_dad})." \
   .format(games=week_games, difference=format(Mat_Wins-Dad_Wins,',.0f'), margin=game_lead,wins_mat=Mat_Wins,losses_mat=Mat_Losses,pct_mat=Mat_Pct,wins_dad=Dad_Wins,losses_dad=Dad_Losses,pct_dad=Dad_Pct)
else:
   picks_text = "Through {games} total games, Mat and Dave are tied! They each have a record of {wins_mat}-{losses_mat} ({pct_mat})." \
   .format(games=week_games,wins_mat=Mat_Wins,losses_mat=Mat_Losses,pct_mat=Mat_Pct)

##format
def color_result(val):
    color = 'green' if val=='W' else 'white'
    return f'background-color: {color}'


### bring in over/under tab
sheet_name="OU"
sh = client.open_by_url(url)
df_ou_full = pd.DataFrame(sh.worksheet(sheet_name).get_all_records())

df_ou_full['Year'] = df_ou_full['Year'].astype(str)

filter = df_ou_full["Team_Wins"] != ""
df_ou = pd.DataFrame(df_ou_full[filter])
df_ou['Year'] = df_ou['Year'].astype(str)

conditions = [
    (df_ou['Result'] == 'P'),
    (df_ou['Result'] == df_ou['Mat']),
    (df_ou['Result'] != df_ou['Mat'])]

# create a list of the values we want to assign for each condition
values = ['Push', 'Win','Loss']

# create a new column and use np.select to assign values to it using our lists as arguments
df_ou['Mat_New'] = np.select(conditions, values)

st.write(df_ou)

'''

conditions = [
    (df_ou['Original_Result'] == 'P'),
    (df_ou['Same Pick'] == 'Different') & (df_ou['Original_Result'] == df_ou['Mat']),
    (df_ou['Same Pick'] == 'Different') & (df_ou['Original_Result'] != df_ou['Mat']),
    (df_ou['Same Pick'] == df_ou['Original_Result']),
    (df_ou['Same Pick'] != df_ou['Original_Result'])]

# create a list of the values we want to assign for each condition
values = ['Push','Win', 'Loss','Win','Loss']

# create a new column and use np.select to assign values to it using our lists as arguments
df_ou['Mat_Original'] = np.select(conditions, values)

conditions = [
    (df_ou['Result'] == 'P'),
    (df_ou['Result'] == df_ou['Dad']),
    (df_ou['Result'] != df_ou['Dad'])]

# create a list of the values we want to assign for each condition
values = ['Push', 'Win','Loss']

# create a new column and use np.select to assign values to it using our lists as arguments
df_ou['Dad_New'] = np.select(conditions, values)

conditions = [
    (df_ou['Original_Result'] == 'P'),
    (df_ou['Same Pick'] == 'Different') & (df_ou['Original_Result'] == df_ou['Dad']),
    (df_ou['Same Pick'] == 'Different') & (df_ou['Original_Result'] != df_ou['Dad']),
    (df_ou['Same Pick'] == df_ou['Original_Result']),
    (df_ou['Same Pick'] != df_ou['Original_Result'])]

# create a list of the values we want to assign for each condition
values = ['Push','Win', 'Loss','Win','Loss']

# create a new column and use np.select to assign values to it using our lists as arguments
df_ou['Dad_Original'] = np.select(conditions, values)

df_ou_tally1 = df_ou
choices = [1, 0, 0.5]
conditions = [df_ou_tally1.Mat_New =='Win', df_ou_tally1.Mat_New =='Loss', df_ou_tally1.Mat_New =='Push']
df_ou_tally1['Wins_Mat_New'] = np.select(conditions, choices)

conditions = [df_ou_tally1.Mat_Original =='Win', df_ou_tally1.Mat_Original =='Loss', df_ou_tally1.Mat_Original =='Push']
df_ou_tally1['Wins_Mat_Original'] = np.select(conditions, choices)

conditions = [df_ou_tally1.Dad_New =='Win', df_ou_tally1.Dad_New =='Loss', df_ou_tally1.Dad_New =='Push']
df_ou_tally1['Wins_Dad_New'] = np.select(conditions, choices)

conditions = [df_ou_tally1.Dad_Original =='Win', df_ou_tally1.Dad_Original =='Loss', df_ou_tally1.Dad_Original =='Push']
df_ou_tally1['Wins_Dad_Original'] = np.select(conditions, choices)


df_ou_tally2 = pd.melt(df_ou_tally1, id_vars=['Year','Team'], value_vars=['Wins_Mat_New','Wins_Mat_Original','Wins_Dad_New','Wins_Dad_Original']).reset_index()
df_ou_tally = df_ou_tally2.groupby(['Year','variable'])['value'].sum().reset_index()

filtered_values = np.where((df_ou_tally["variable"] == "Wins_Mat_New") | (df_ou_tally["variable"] == "Wins_Dad_New"))
df_ou_new = df_ou_tally.loc[filtered_values]
df_ou_new['variable'] = df_ou_new['variable'].astype('category')
df_ou_new['variable'] = df_ou_new['variable'].cat.rename_categories({'Wins_Dad_New': 'Dave', 'Wins_Mat_New': 'Mat'})
df_ou_new = df_ou_new.rename(columns={'variable': 'Participant', 'value': 'Wins'})

filtered_values = np.where((df_ou_tally["variable"] == "Wins_Mat_Original") | (df_ou_tally["variable"] == "Wins_Dad_Original"))
df_ou_original = df_ou_tally.loc[filtered_values]
df_ou_original['variable'] = df_ou_original['variable'].astype('category')
df_ou_original['variable'] = df_ou_original['variable'].cat.rename_categories({'Wins_Dad_Original': 'Dave', 'Wins_Mat_Original': 'Mat'})
df_ou_original = df_ou_original.rename(columns={'variable': 'Participant', 'value': 'Wins'})


ou_new = alt.Chart(df_ou_new).mark_bar().encode(
x=alt.X('Participant:O', title=None),
y='Wins:Q',
color='Participant:N',
column='Year:N'
).properties(title='Over/Unders')

ou_original = alt.Chart(df_ou_original).mark_bar().encode(
x=alt.X('Participant:O', title=None),
y='Wins:Q',
color='Participant:N',
column='Year:N'
).properties(title='Original Over/Unders')

current_year = max(df_ou_full.Year)
df_ou_current = df_ou_full.loc[np.where(df_ou_full["Year"]==current_year)]
df_ou_current = df_ou_current[["Year","Team", "Wins","Adjusted","Mat","Dad","Who Changed?"]]

### cardinals games

filter = df_picks["Mat Result"] != ""
df_picks_year1 = pd.DataFrame(df_picks[filter]).reset_index()

filtered_values = np.where((df_picks_year1["Away"] == "Cardinals") | (df_picks_year1["Home"] == "Cardinals"))
df_picks_cards1 = df_picks.loc[filtered_values]

df_picks_cards2 = pd.melt(df_picks_cards1, id_vars=['Year'], value_vars=['Mat Result','Dad Result']).reset_index()

conditions = [df_picks_cards2.value =='W', df_picks_cards2.value =='L', df_picks_cards2.value =='T']
choices = [1, 0, 0.5]

df_picks_cards2['Wins'] = np.select(conditions, choices)

df_picks_cards = df_picks_cards2.groupby(['Year','variable'])['Wins'].agg([('Games','size'), ('Win_Total','sum')]).reset_index()
df_picks_cards['Pct'] = df_picks_cards['Win_Total'].div(df_picks_cards['Games'], axis=0)

df_picks_cards['variable'] = df_picks_cards['variable'].astype('category')
df_picks_cards['variable'] = df_picks_cards['variable'].cat.rename_categories({'Mat Result': 'Mat', 'Dad Result': 'Dave'})
df_picks_cards = df_picks_cards.rename(columns={'variable': 'Participant', 'Pct': 'Win Percentage'})

win_pct_cards = alt.Chart(df_picks_cards).mark_bar().encode(
x=alt.X('Participant:O', title=None),
y='Win Percentage:Q',
color='Participant:N',
column='Year:N'
).properties(title='Cardinals Games')

## overall cards wins and win pct

df_picks_cards_overall1 = pd.melt(df_picks_cards1, id_vars=['Year'], value_vars=['Mat Result','Dad Result']).reset_index()

conditions = [df_picks_cards_overall1.value =='W', df_picks_cards_overall1.value =='L', df_picks_cards_overall1.value =='T']
choices = [1, 0, 0.5]

df_picks_cards_overall1['Wins'] = np.select(conditions, choices)

df_picks_cards_overall = df_picks_cards_overall1.groupby(['variable'])['Wins'].agg([('Games','size'), ('Win_Total','sum')]).reset_index()
df_picks_cards_overall['Pct'] = df_picks_cards_overall['Win_Total'].div(df_picks_cards_overall['Games'], axis=0)

df_cards_mat = pd.DataFrame(df_picks_cards_overall[df_picks_cards_overall['variable']=='Mat Result'])
df_cards_dad = pd.DataFrame(df_picks_cards_overall[df_picks_cards_overall['variable']=='Dad Result'])

Mat_Cards_Wins = df_cards_mat.iloc[0]['Win_Total']
Mat_Cards_Losses = df_cards_mat.iloc[0]['Games'] - df_cards_mat.iloc[0]['Win_Total']
Mat_Cards_Pct = round(df_cards_mat.iloc[0]['Pct'],3)

Dad_Cards_Wins = df_cards_dad.iloc[0]['Win_Total']
Dad_Cards_Losses = df_cards_dad.iloc[0]['Games'] - df_cards_dad.iloc[0]['Win_Total']
Dad_Cards_Pct = round(df_cards_dad.iloc[0]['Pct'],3)


if Dad_Cards_Wins>Mat_Cards_Wins:
   cards_text = "Dave has a better win percentage in Cardinals games, with a record of {wins_dad}-{losses_dad} ({pct_dad}). Mat's record is {wins_mat}-{losses_mat} ({pct_mat})." \
   .format(wins_dad=Dad_Cards_Wins,losses_dad=Dad_Cards_Losses,pct_dad=Dad_Cards_Pct,wins_mat=Mat_Cards_Wins,losses_mat=Mat_Cards_Losses,pct_mat=Mat_Cards_Pct)
elif Dad_Cards_Wins<Mat_Cards_Wins:
   cards_text = "Mat leads Dave in picking Cardinals games. Mat's record is {wins_mat}-{losses_mat} ({pct_mat}) and Dave's is {wins_dad}-{losses_dad} ({pct_dad})." \
   .format(wins_mat=Mat_Cards_Wins,losses_mat=Mat_Cards_Losses,pct_mat=Mat_Cards_Pct,wins_dad=Dad_Cards_Wins,losses_dad=Dad_Cards_Losses,pct_dad=Dad_Cards_Pct)
else:
   cards_text = "Mat and Dave are tied when picking Cardinals games! They each have a record of {wins_mat}-{losses_mat} ({pct_mat})." \
   .format(wins_mat=Mat_Cards_Wins,losses_mat=Mat_Cards_Losses,pct_mat=Mat_Cards_Pct)


### all teams matrix

df_picks_home = df_picks.rename(columns={"Home": "Team"}).drop(columns=['Away']).reset_index()
df_picks_away = df_picks.rename(columns={"Away": "Team"}).drop(columns=['Home']).reset_index()
df_picks_teams1 = pd.concat([df_picks_home, pd.DataFrame(df_picks_away)], ignore_index=True)


df_picks_teams2 = pd.melt(df_picks_teams1, id_vars=['Team'], value_vars=['Mat Pick','Dad Pick','Mat Result','Dad Result']).reset_index()


filter = df_picks_teams2["variable"].isin(['Mat Result','Dad Result'])
df_picks_won = pd.DataFrame(df_picks_teams2[filter])

conditions = [df_picks_won.value =='W', df_picks_won.value =='L', df_picks_won.value =='T']
choices = [1, 0, 0.5]

df_picks_won['Wins'] = np.select(conditions, choices)
df_picks_won = df_picks_won.groupby(['Team','variable'])['Wins'].agg([('Games','size'), ('Win_Total','sum')]).reset_index()
df_picks_won['variable'] = df_picks_won['variable'].astype('category')
df_picks_won['variable'] = df_picks_won['variable'].cat.rename_categories({'Mat Result': 'Mat', 'Dad Result': 'Dave'})

filter = df_picks_teams2["variable"].isin(['Mat Pick','Dad Pick'])
df_picks_picked = pd.DataFrame(df_picks_teams2[filter])

conditions = [df_picks_picked.value == df_picks_picked.Team, df_picks_picked.value != df_picks_picked.Team]
choices = [1, 0]

df_picks_picked['Pick'] = np.select(conditions, choices)
df_picks_picked = df_picks_picked.groupby(['Team','variable'])['Pick'].agg([('Pick_Total','sum')]).reset_index()
df_picks_picked['variable'] = df_picks_picked['variable'].astype('category')
df_picks_picked['variable'] = df_picks_picked['variable'].cat.rename_categories({'Mat Pick': 'Mat', 'Dad Pick': 'Dave'})

df_picks_teams = pd.merge(df_picks_won,df_picks_picked,  how='left', left_on=['Team','variable'], right_on = ['Team','variable'])

df_picks_teams['Win Percentage'] = df_picks_teams['Win_Total'].div(df_picks_teams['Games'], axis=0)
df_picks_teams['Pick Percentage'] = df_picks_teams['Pick_Total'].div(df_picks_teams['Games'], axis=0)
df_picks_teams = df_picks_teams.rename(columns={'variable': 'Participant', 'Win_Total': 'Wins', 'Pick_Total': 'Picked'})

average_picked = df_picks_teams[["Picked"]].mean()
df_mat_teams = pd.DataFrame(df_picks_teams[df_picks_teams['Participant']=='Mat'])
df_dad_teams = pd.DataFrame(df_picks_teams[df_picks_teams['Participant']=='Dave'])

#Mat_Most_Picks =df_mat_teams.loc[df_mat_teams['Picked']==69,'Team'].iloc[0]
#Mat_Most_Wins = df_mat_teams.iloc[0]['Games'] - df_cards_mat.iloc[0]['Win_Total']
#Mat_Cards_Wins = round(df_cards_mat.iloc[0]['Pct'],3)

#Dad_Cards_Wins = df_cards_dad.iloc[0]['Win_Total']
#Dad_Cards_Losses = df_cards_dad.iloc[0]['Games'] - df_cards_dad.iloc[0]['Win_Total']
#Dad_Cards_Pct = round(df_cards_dad.iloc[0]['Pct'],3)

   
teams_mat = px.scatter(
    df_mat_teams,
    x="Picked",
    y="Win Percentage",
    text='Team',
    color="Win Percentage",
    color_continuous_scale="viridis",
    title="Mat's Win Percentage and Times Picked for Each Team"
).add_hline(y=0.65)

teams_dad = px.scatter(
    df_dad_teams,
    x="Picked",
    y="Win Percentage",
    text='Team',
    color="Win Percentage",
    color_continuous_scale="viridis",
    title="Dave's Win Percentage and Times Picked for Each Team"
).add_hline(y=0.65)

df_teams_tally1 = df_picks_won.pivot(index='Team', columns='variable')['Win_Total'].reset_index()
df_teams_tally2 = df_picks_picked.pivot(index='Team', columns='variable')['Pick_Total'].reset_index()
df_teams_tally3 = df_picks_won.pivot(index='Team', columns='variable')['Games'].reset_index()

df_teams_tally4 = pd.merge(df_teams_tally3,df_teams_tally2,  how='left', left_on=['Team'], right_on = ['Team']).reset_index()
df_teams_tally = pd.merge(df_teams_tally4,df_teams_tally1,  how='left', left_on=['Team'], right_on = ['Team']).reset_index()

df_teams_tally['Dave Win Pct'] = df_teams_tally['Dave'].div(df_teams_tally['Dave_x'], axis=0)
df_teams_tally['Dave Pick Pct'] = df_teams_tally['Dave_y'].div(df_teams_tally['Dave_x'], axis=0)
df_teams_tally['Mat Win Pct'] = df_teams_tally['Mat'].div(df_teams_tally['Mat_x'], axis=0)
df_teams_tally['Mat Pick Pct'] = df_teams_tally['Mat_y'].div(df_teams_tally['Mat_x'], axis=0)
df_teams_tally = df_teams_tally.rename(columns={'Dave_x': 'Games', 'Dave': 'Dave Wins', 'Dave_y': 'Dave Picked', 'Mat': 'Mat Wins', 'Mat_y': 'Mat Picked'})
df_teams_tally['Pick Difference'] = abs(df_teams_tally['Dave Picked']-df_teams_tally['Mat Picked'])
df_teams_tally['Win Difference'] = abs(df_teams_tally['Dave Wins']-df_teams_tally['Mat Wins'])

df_teams_tally = df_teams_tally.loc[:,['Team','Games','Mat Picked','Dave Picked','Pick Difference','Mat Wins','Mat Win Pct','Dave Wins','Dave Win Pct','Win Difference']]


### tallies of picks, over/unders, and cards games

picks_tally = df_picks_year2.pivot(index='Year', columns='Participant')['Win Percentage'].rename(columns={'Dave': 'Dave: Win Pct', 'Mat': 'Mat: Win Pct'}).reset_index()
picks_tally['Year'] = picks_tally['Year'].astype(str)
ou_tally = df_ou_tally.pivot(index='Year', columns='variable')['value'].rename(columns={'Wins_Dad_New': 'Dave: OU Wins', 'Wins_Dad_Original': 'Dave: OU Wins Original', 'Wins_Mat_New': 'Mat: OU Wins', 'Wins_Mat_Original': 'Mat: OU Wins Original'})
cards_tally = df_picks_cards.pivot(index='Year', columns='Participant')['Win Percentage'].rename(columns={'Dave': 'Dave: Cards Win Pct', 'Mat': 'Mat: Cards Win Pct'}).reset_index()
cards_tally['Year'] = cards_tally['Year'].astype(str)

total_tally1 = pd.merge(picks_tally,ou_tally,  how='left', left_on=['Year'], right_on = ['Year']).reset_index()
total_tally = pd.merge(total_tally1,cards_tally,  how='left', left_on=['Year'], right_on = ['Year']).reset_index()

total_tally = total_tally.loc[:,['Year','Dave: Win Pct','Mat: Win Pct','Dave: OU Wins','Dave: OU Wins Original','Mat: OU Wins','Mat: OU Wins Original','Dave: Cards Win Pct','Mat: Cards Win Pct']]

#color palette options
cm_tally = sns.light_palette("green", as_cmap=True)

##automated text
dave_top_year = total_tally.loc[total_tally['Dave: Win Pct'] == total_tally['Dave: Win Pct'].max(), 'Year'].values[0]
dave_top_pct = format(total_tally.loc[total_tally['Dave: Win Pct'] == total_tally['Dave: Win Pct'].max(), 'Dave: Win Pct'].values[0],'.3f')

mat_top_year = total_tally.loc[total_tally['Mat: Win Pct'] == total_tally['Mat: Win Pct'].max(), 'Year'].values[0]
mat_top_pct = format(total_tally.loc[total_tally['Mat: Win Pct'] == total_tally['Mat: Win Pct'].max(), 'Mat: Win Pct'].values[0],'.3f')

##weekly summary table

df_picks_week12 = df_picks_week1.groupby(['Year','Week','variable'])['Wins'].agg([('Games','size'), ('Win_Total','sum')]).reset_index()
df_picks_week12['Pct'] = df_picks_week12['Win_Total'].div(df_picks_week12['Games'], axis=0)
df_picks_week12 = df_picks_week12.rename(columns={'variable': 'Participant', 'Win_Total': 'Wins', 'Pct': 'Win Percentage'})
df_picks_week12['Year'] = df_picks_week12['Year'].astype('string')
df_picks_week12['Participant'] = df_picks_week12['Participant'].astype('category')
df_picks_week12['Participant'] = df_picks_week12['Participant'].cat.rename_categories({'Mat Result': 'Mat', 'Dad Result': 'Dave'})


#color palette options
cm_wins = sns.light_palette("green", as_cmap=True)

################################################ tabs #####################################################
   
with tab1:
   st.header("Picks")
   st.write(picks_text)
   st.dataframe(df_results_current, hide_index=True)
   st.write("Here are the picks with {remaining} games left in Week {week}.".format(remaining=remaining_count,week=current_week))
   st.dataframe(df_picks_current.style.applymap(color_result, subset=['Mat Result','Dad Result']), hide_index=True)
   st.write("Dave and Mat picked {different} games differently in Week {week}.".format(different=different_count,week=current_week))
   st.dataframe(df_picks_different.style.applymap(color_result, subset=['Mat Result','Dad Result']), hide_index=True)
   st.write("See how the current win percentages stack up to prior seasons. For comparison, Mat's best overall season ",\
             "({matpct}) was in {matyear} and Dave's ({davepct}) was in {daveyear}.".format(matpct=mat_top_pct,matyear=mat_top_year,davepct=dave_top_pct,daveyear=dave_top_year))
   st.plotly_chart(weekly_pct, theme=None)
   st.write("Compare overall winning percentages over the years.")
   st.altair_chart(win_pct, use_container_width=False)


with tab2:
   st.header("Over/Under")
   st.write("Check out the Over/Under picks for {year}.".format(year=current_year))
   st.dataframe(df_ou_current, hide_index=True)
   st.altair_chart(ou_new, use_container_width=False)
   st.altair_chart(ou_original, use_container_width=False)

with tab3:
   st.header("Teams")
   st.write(cards_text)
   st.altair_chart(win_pct_cards, use_container_width=False)
   st.write("Here's a table of how the picks have gone for each NFL team.") # I NEED TO AUTOMATE THE TEXT FOR THIS
   st.dataframe(df_teams_tally, hide_index=True)
   st.plotly_chart(teams_mat, theme=None, use_container_width=True)
   st.plotly_chart(teams_dad, theme=None, use_container_width=True)


with tab4:
   st.header("Tallies") # AUTOMATE TEXT HERE...also, should I just combine everything into one table?
   st.write("Below are the tallies for picks, over/unders, and Cardinals games over the years.")
   st.dataframe(total_tally.style.background_gradient(cmap=cm_tally).highlight_null('white'),hide_index=True,use_container_width=True)

with tab5:
   st.header("Full History")
   st.write("Below is the full history of picks for each week, dating back to 2011.")
   st.dataframe(df_picks.style, hide_index=True)
   st.write("And here are the weekly summaries.")
   st.dataframe(df_picks_week12.style.format({'Wins': "{:.0f}",'Win Percentage': "{:.3f}"}).\
                background_gradient(cmap=cm_wins,subset=['Wins', 'Win Percentage']),hide_index=True,use_container_width=True)
   st.write("Here's the full history of Over/Unders going back to 2017.")
   st.dataframe(df_ou_full.style, hide_index=True)

'''
