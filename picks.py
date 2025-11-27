import streamlit as st
import pandas as pd
import gspread
import numpy as np
import plotly.express as px
import seaborn as sns
from google.oauth2.service_account import Credentials

########################### TO DO LIST #################################
#### more call-outs in various spots
#### fix team scatterplots - dashed vertical and horizontal lines
#### for comparison call-outs, need to filter out current season
#### formatting on tallies table

# Auth
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
skey = st.secrets["gcp_service_account"]
credentials = Credentials.from_service_account_info(skey, scopes=scopes)
client = gspread.authorize(credentials)
url = st.secrets["private_gsheets_url"]

# App
st.set_page_config(page_title="NFL Picks")
st.title("NFL Picks")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Picks", "Over/Under","Teams", "Tallies", "Full History"])

# Helpers
def result_to_win(val):
    return {"W": 1, "L": 0, "T": 0.5}.get(val, np.nan)

def ou_result_to_win(val):
    return {"Win": 1, "Loss": 0, "Push": 0.5}.get(val, np.nan)

def color_result(val):
    color = 'green' if val=='W' else 'white'
    return f'background-color: {color}'

# Load sheets
sh = client.open_by_url(url)

#############################
# Picks base frame
#############################
df_picks = pd.DataFrame(sh.worksheet("Picks").get_all_records())

# Yearly picks summary
df_picks_year2 = (
    df_picks.query("`Mat Result` != ''")
    .melt(id_vars=["Year"], value_vars=["Mat Result","Dad Result"], var_name="Participant", value_name="Result")
    .assign(Wins=lambda d: d["Result"].map(result_to_win))
    .groupby(["Year","Participant"])
    .agg(Games=("Wins","size"), Wins=("Wins","sum"))
    .reset_index()
    .assign(**{"Win Percentage": lambda d: d["Wins"]/d["Games"]})
    .replace({"Participant": {"Mat Result":"Mat","Dad Result":"Dave"}})
)

# Chart: Win pct by year (Plotly)
win_pct = px.bar(
    df_picks_year2,
    x="Participant",
    y="Win Percentage",
    color="Participant",
    facet_col="Year",
    title="Win Percentage by Year"
)

#############################
# Weekly cumulative
#############################
df_picks_week = (
    df_picks.query("`Mat Result` != ''")
    .melt(id_vars=["Year","Week"], value_vars=["Mat Result","Dad Result"], var_name="Participant", value_name="Result")
    .assign(Wins=lambda d: d["Result"].map(result_to_win))
)

df_weekly = (
    df_picks_week.groupby(["Year","Week","Participant"])
    .agg(Games=("Wins","size"), Wins=("Wins","sum"))
    .reset_index()
)

df_weekly["Cumulative Wins"] = df_weekly.groupby(["Year","Participant"])["Wins"].cumsum()
df_weekly["Cumulative Games"] = df_weekly.groupby(["Year","Participant"])["Games"].cumsum()
df_weekly["Cumulative Win Percentage"] = df_weekly["Cumulative Wins"] / df_weekly["Cumulative Games"]
df_weekly["Participant"] = df_weekly["Participant"].replace({"Mat Result":"Mat","Dad Result":"Dave"})

weekly_pct = px.line(
    df_weekly,
    x="Week",
    y="Cumulative Win Percentage",
    color="Year",
    line_dash="Participant",
    title="Cumulative Win Percentage by Year"
)

#############################
# Current week block
#############################
df_picks_current1 = df_picks.query("`Mat Pick` != ''")
current_year = int(df_picks_current1["Year"].max())
df_picks_current2 = df_picks_current1.query("Year == @current_year")
current_week = int(df_picks_current2["Week"].max())
df_picks_current = df_picks_current2.query("Week == @current_week").reset_index(drop=True)

remaining_count = df_picks_current.query("`Mat Result` == ''").shape[0]
df_picks_different = df_picks_current.query("`Mat Pick` != `Dad Pick`")
different_count = df_picks_different.shape[0]

# Current year summary tables
df_results_current = df_picks_year2.query("Year == @current_year").reset_index(drop=True)
df_results_current["Year"] = df_results_current["Year"].astype(str)

df_results_current_week = (
    df_weekly.query("Year == @current_year")
    .sort_values("Week")
    .groupby(["Participant"], as_index=False)
    .tail(1)
)

df_results_current_Mat = df_results_current.query("Participant == 'Mat'")
df_results_current_Dad = df_results_current.query("Participant == 'Dave'")

week_games = int(df_results_current_week.iloc[0]["Games"])

Mat_Wins = float(df_results_current_Mat.iloc[0]["Wins"])
Mat_Losses = float(df_results_current_Mat.iloc[0]["Games"] - df_results_current_Mat.iloc[0]["Wins"])
Mat_Pct = round(float(df_results_current_Mat.iloc[0]["Win Percentage"]), 3)

Dad_Wins = float(df_results_current_Dad.iloc[0]["Wins"])
Dad_Losses = float(df_results_current_Dad.iloc[0]["Games"] - df_results_current_Dad.iloc[0]["Wins"])
Dad_Pct = round(float(df_results_current_Dad.iloc[0]["Win Percentage"]), 3)

diff = abs(Mat_Wins - Dad_Wins)
game_lead = "games" if diff > 1 else "game"

if Dad_Wins > Mat_Wins:
    picks_text = (
        "Through {games} total games, Dave is ahead of Mat by {difference} {margin}. "
        "Dave's record is {wins_dad}-{losses_dad} ({pct_dad}) and Mat's is {wins_mat}-{losses_mat} ({pct_mat})."
        .format(
            games=week_games,
            difference=format(Dad_Wins - Mat_Wins, ",.0f"),
            margin=game_lead,
            wins_dad=Dad_Wins,
            losses_dad=Dad_Losses,
            pct_dad=Dad_Pct,
            wins_mat=Mat_Wins,
            losses_mat=Mat_Losses,
            pct_mat=Mat_Pct
        )
    )
elif Dad_Wins < Mat_Wins:
    picks_text = (
        "Through {games} total games, Mat leads Dave by {difference} {margin}. "
        "Mat's record is {wins_mat}-{losses_mat} ({pct_mat}) and Dave's is {wins_dad}-{losses_dad} ({pct_dad})."
        .format(
            games=week_games,
            difference=format(Mat_Wins - Dad_Wins, ",.0f"),
            margin=game_lead,
            wins_mat=Mat_Wins,
            losses_mat=Mat_Losses,
            pct_mat=Mat_Pct,
            wins_dad=Dad_Wins,
            losses_dad=Dad_Losses,
            pct_dad=Dad_Pct
        )
    )
else:
    picks_text = (
        "Through {games} total games, Mat and Dave are tied! "
        "They each have a record of {wins_mat}-{losses_mat} ({pct_mat})."
        .format(games=week_games, wins_mat=Mat_Wins, losses_mat=Mat_Losses, pct_mat=Mat_Pct)
    )

#############################
# Over/Under
#############################
df_ou_full = pd.DataFrame(sh.worksheet("OU").get_all_records())
df_ou_full["Year"] = df_ou_full["Year"].astype(str)

df_ou = df_ou_full.query("Team_Wins != ''").copy()

# New outcomes
df_ou["Mat_New"] = np.where(
    df_ou["Result"].eq("P"), "Push",
    np.where(df_ou["Result"].eq(df_ou["Mat"]), "Win", "Loss")
)
df_ou["Dad_New"] = np.where(
    df_ou["Result"].eq("P"), "Push",
    np.where(df_ou["Result"].eq(df_ou["Dad"]), "Win", "Loss")
)

# Original outcomes (preserves your logic)
df_ou["Mat_Original"] = np.select(
    [
        df_ou["Original_Result"].eq("P"),
        (df_ou["Same Pick"].eq("Different")) & (df_ou["Original_Result"].eq(df_ou["Mat"])),
        (df_ou["Same Pick"].eq("Different")) & (df_ou["Original_Result"].ne(df_ou["Mat"])),
        df_ou["Same Pick"].eq(df_ou["Original_Result"]),
        df_ou["Same Pick"].ne(df_ou["Original_Result"]),
    ],
    ["Push","Win","Loss","Win","Loss"],
    default="Win",
)
df_ou["Dad_Original"] = np.select(
    [
        df_ou["Original_Result"].eq("P"),
        (df_ou["Same Pick"].eq("Different")) & (df_ou["Original_Result"].eq(df_ou["Dad"])),
        (df_ou["Same Pick"].eq("Different")) & (df_ou["Original_Result"].ne(df_ou["Dad"])),
        df_ou["Same Pick"].eq(df_ou["Original_Result"]),
        df_ou["Same Pick"].ne(df_ou["Original_Result"]),
    ],
    ["Push","Win","Loss","Win","Loss"],
    default="Win",
)

# Tally conversions
df_ou_tally1 = df_ou.assign(
    Wins_Mat_New=lambda d: d["Mat_New"].map(ou_result_to_win),
    Wins_Mat_Original=lambda d: d["Mat_Original"].map(ou_result_to_win),
    Wins_Dad_New=lambda d: d["Dad_New"].map(ou_result_to_win),
    Wins_Dad_Original=lambda d: d["Dad_Original"].map(ou_result_to_win),
)

df_ou_tally = (
    df_ou_tally1
    .melt(
        id_vars=["Year","Team"],
        value_vars=["Wins_Mat_New","Wins_Mat_Original","Wins_Dad_New","Wins_Dad_Original"]
    )
    .groupby(["Year","variable"], as_index=False)["value"].sum()
)

# New vs Original subsets for charts
df_ou_new = (
    df_ou_tally.query("variable in ['Wins_Mat_New','Wins_Dad_New']")
    .replace({"variable":{"Wins_Mat_New":"Mat","Wins_Dad_New":"Dave"}})
    .rename(columns={"variable":"Participant","value":"Wins"})
)
df_ou_original = (
    df_ou_tally.query("variable in ['Wins_Mat_Original','Wins_Dad_Original']")
    .replace({"variable":{"Wins_Mat_Original":"Mat","Wins_Dad_Original":"Dave"}})
    .rename(columns={"variable":"Participant","value":"Wins"})
)

ou_new = px.bar(
    df_ou_new,
    x="Participant",
    y="Wins",
    color="Participant",
    facet_col="Year",
    title="Over/Unders"
)
ou_original = px.bar(
    df_ou_original,
    x="Participant",
    y="Wins",
    color="Participant",
    facet_col="Year",
    title="Original Over/Unders"
)

current_year_str = df_ou_full["Year"].max()
df_ou_current = (
    df_ou_full.query("Year == @current_year_str")[["Year","Team","Wins","Adjusted","Mat","Dad","Who Changed?"]]
)

#############################
# Cardinals (team-specific)
#############################
df_picks_cards = (
    df_picks.query("`Mat Result` != '' and (Home == 'Cardinals' or Away == 'Cardinals')")
    .melt(id_vars=["Year"], value_vars=["Mat Result","Dad Result"], var_name="Participant", value_name="Result")
    .assign(Wins=lambda d: d["Result"].map(result_to_win))
    .groupby(["Year","Participant"])
    .agg(Games=("Wins","size"), Win_Total=("Wins","sum"))
    .reset_index()
    .assign(**{"Win Percentage": lambda d: d["Win_Total"]/d["Games"]})
    .replace({"Participant": {"Mat Result":"Mat","Dad Result":"Dave"}})
)

win_pct_cards = px.bar(
    df_picks_cards,
    x="Participant",
    y="Win Percentage",
    color="Participant",
    facet_col="Year",
    title="Cardinals Games"
)

# Overall Cardinals summary text
df_cards_overall = (
    df_picks.query("`Mat Result` != '' and (Home == 'Cardinals' or Away == 'Cardinals')")
    .melt(id_vars=["Year"], value_vars=["Mat Result","Dad Result"], var_name="Participant", value_name="Result")
    .assign(Wins=lambda d: d["Result"].map(result_to_win))
    .groupby(["Participant"])
    .agg(Games=("Wins","size"), Win_Total=("Wins","sum"))
    .reset_index()
)

df_cards_overall["Pct"] = df_cards_overall["Win_Total"] / df_cards_overall["Games"]
df_cards_overall = df_cards_overall.replace({"Participant":{"Mat Result":"Mat","Dad Result":"Dave"}})

Mat_Cards_Wins = int(df_cards_overall.query("Participant=='Mat'")["Win_Total"].iloc[0])
Mat_Cards_Losses = int(df_cards_overall.query("Participant=='Mat'")["Games"].iloc[0] - Mat_Cards_Wins)
Mat_Cards_Pct = round(float(df_cards_overall.query("Participant=='Mat'")["Pct"].iloc[0]), 3)

Dad_Cards_Wins = int(df_cards_overall.query("Participant=='Dave'")["Win_Total"].iloc[0])
Dad_Cards_Losses = int(df_cards_overall.query("Participant=='Dave'")["Games"].iloc[0] - Dad_Cards_Wins)
Dad_Cards_Pct = round(float(df_cards_overall.query("Participant=='Dave'")["Pct"].iloc[0]), 3)

if Dad_Cards_Wins > Mat_Cards_Wins:
    cards_text = (
        "Dave has a better win percentage in Cardinals games, with a record of "
        f"{Dad_Cards_Wins}-{Dad_Cards_Losses} ({Dad_Cards_Pct}). "
        f"Mat's record is {Mat_Cards_Wins}-{Mat_Cards_Losses} ({Mat_Cards_Pct})."
    )
elif Dad_Cards_Wins < Mat_Cards_Wins:
    cards_text = (
        "Mat leads Dave in picking Cardinals games. "
        f"Mat's record is {Mat_Cards_Wins}-{Mat_Cards_Losses} ({Mat_Cards_Pct}) "
        f"and Dave's is {Dad_Cards_Wins}-{Dad_Cards_Losses} ({Dad_Cards_Pct})."
    )
else:
    cards_text = (
        "Mat and Dave are tied when picking Cardinals games! "
        f"They each have a record of {Mat_Cards_Wins}-{Mat_Cards_Losses} ({Mat_Cards_Pct})."
    )

#############################
# Teams matrix and tallies
#############################
df_picks_home = df_picks.rename(columns={"Home":"Team"}).drop(columns=["Away"])
df_picks_away = df_picks.rename(columns={"Away":"Team"}).drop(columns=["Home"])
df_picks_teams_all = pd.concat([df_picks_home, df_picks_away], ignore_index=True)

# Wins by team/participant
df_picks_won = (
    df_picks_teams_all.melt(id_vars=["Team"], value_vars=["Mat Result","Dad Result"], var_name="Participant", value_name="Result")
    .assign(Wins=lambda d: d["Result"].map(result_to_win))
    .groupby(["Team","Participant"])
    .agg(Games=("Wins","size"), Win_Total=("Wins","sum"))
    .reset_index()
    .replace({"Participant":{"Mat Result":"Mat","Dad Result":"Dave"}})
)

# Picked by team/participant
df_picks_picked = (
    df_picks_teams_all.melt(id_vars=["Team"], value_vars=["Mat Pick","Dad Pick"], var_name="Participant", value_name="Pick")
    .assign(Picked=lambda d: (d["Pick"] == d["Team"]).astype(int))
    .groupby(["Team","Participant"])
    .agg(Pick_Total=("Picked","sum"))
    .reset_index()
    .replace({"Participant":{"Mat Pick":"Mat","Dad Pick":"Dave"}})
)

# Merge summaries
df_picks_teams = (
    pd.merge(df_picks_won, df_picks_picked, on=["Team","Participant"], how="left")
    .assign(
        **{
            "Win Percentage": lambda d: d["Win_Total"] / d["Games"],
            "Pick Percentage": lambda d: d["Pick_Total"] / d["Games"],
            "Wins": lambda d: d["Win_Total"],
            "Picked": lambda d: d["Pick_Total"],
        }
    )
    .drop(columns=["Win_Total","Pick_Total"])
)

df_mat_teams = df_picks_teams.query("Participant=='Mat'")
df_dad_teams = df_picks_teams.query("Participant=='Dave'")

teams_mat = px.scatter(
    df_mat_teams,
    x="Picked",
    y="Win Percentage",
    text="Team",
    color="Win Percentage",
    color_continuous_scale="viridis",
    title="Mat's Win Percentage and Times Picked for Each Team"
).add_hline(y=0.65)

teams_dad = px.scatter(
    df_dad_teams,
    x="Picked",
    y="Win Percentage",
    text="Team",
    color="Win Percentage",
    color_continuous_scale="viridis",
    title="Dave's Win Percentage and Times Picked for Each Team"
).add_hline(y=0.65)

# Team tally table (compact)
df_teams_tally = (
    df_picks_teams
    .pivot(index="Team", columns="Participant", values=["Games","Wins","Picked","Win Percentage"])
)

# Flatten MultiIndex columns
df_teams_tally.columns = [f"{a} {b}".strip() for a,b in df_teams_tally.columns]
df_teams_tally = df_teams_tally.reset_index()

# Differences and selection
df_teams_tally = (
    df_teams_tally
    .assign(
        **{
            "Pick Difference": (df_teams_tally["Picked Dave"] - df_teams_tally["Picked Mat"]).abs(),
            "Win Difference": (df_teams_tally["Wins Dave"] - df_teams_tally["Wins Mat"]).abs(),
            "Dave Win Pct": df_teams_tally["Win Percentage Dave"],
            "Mat Win Pct": df_teams_tally["Win Percentage Mat"],
            "Games": df_teams_tally["Games Dave"],  # same as Games Mat typically
        }
    )
    .loc[:,["Team","Games","Picked Mat","Picked Dave","Pick Difference",
            "Wins Mat","Dave Win Pct","Wins Dave","Mat Win Pct","Win Difference"]]
    .rename(columns={
        "Picked Mat":"Mat Picked",
        "Picked Dave":"Dave Picked",
        "Wins Mat":"Mat Wins",
        "Wins Dave":"Dave Wins"
    })
)

#############################
# Tallies across years
#############################
picks_tally = (
    df_picks_year2
    .pivot(index="Year", columns="Participant", values="Win Percentage")
    .rename(columns={"Dave":"Dave: Win Pct","Mat":"Mat: Win Pct"})
    .reset_index()
    .assign(Year=lambda d: d["Year"].astype(str))
)

ou_tally = (
    df_ou_tally
    .pivot(index="Year", columns="variable", values="value")
    .rename(columns={
        "Wins_Dad_New":"Dave: OU Wins",
        "Wins_Dad_Original":"Dave: OU Wins Original",
        "Wins_Mat_New":"Mat: OU Wins",
        "Wins_Mat_Original":"Mat: OU Wins Original"
    })
    .reset_index()
)

cards_tally = (
    df_picks_cards
    .pivot(index="Year", columns="Participant", values="Win Percentage")
    .rename(columns={"Dave":"Dave: Cards Win Pct","Mat":"Mat: Cards Win Pct"})
    .reset_index()
    .assign(Year=lambda d: d["Year"].astype(str))
)

total_tally = (
    picks_tally
    .merge(ou_tally, on="Year", how="left")
    .merge(cards_tally, on="Year", how="left")
    .loc[:,[
        "Year","Dave: Win Pct","Mat: Win Pct",
        "Dave: OU Wins","Dave: OU Wins Original",
        "Mat: OU Wins","Mat: OU Wins Original",
        "Dave: Cards Win Pct","Mat: Cards Win Pct"
    ]]
)

# Automated text for top seasons
dave_top_year, dave_top_pct = total_tally.loc[total_tally["Dave: Win Pct"].idxmax(), ["Year","Dave: Win Pct"]]
mat_top_year, mat_top_pct = total_tally.loc[total_tally["Mat: Win Pct"].idxmax(), ["Year","Mat: Win Pct"]]
dave_top_pct = f"{dave_top_pct:.3f}"
mat_top_pct = f"{mat_top_pct:.3f}"

#############################
# Weekly summary table
#############################
df_picks_week12 = (
    df_picks_week
    .groupby(["Year","Week","Participant"])
    .agg(Games=("Wins","size"), Win_Total=("Wins","sum"))
    .reset_index()
    .assign(**{"Win Percentage": lambda d: d["Win_Total"] / d["Games"]})
    .rename(columns={"Win_Total":"Wins"})
    .assign(Year=lambda d: d["Year"].astype(str))
)

#############################
# Styles
#############################
cm_tally = sns.light_palette("green", as_cmap=True)
cm_wins = sns.light_palette("green", as_cmap=True)

#############################
# Tabs render
#############################
with tab1:
    st.header("Picks")
    st.write(picks_text)
    st.dataframe(df_results_current, hide_index=True)
    st.write(f"Here are the picks with {remaining_count} games left in Week {current_week}.")
    st.dataframe(df_picks_current.style.applymap(color_result, subset=["Mat Result","Dad Result"]), hide_index=True)
    st.write(f"Dave and Mat picked {different_count} games differently in Week {current_week}.")
    st.dataframe(df_picks_different.style.applymap(color_result, subset=["Mat Result","Dad Result"]), hide_index=True)
    st.write(
        "See how the current win percentages stack up to prior seasons. For comparison, "
        f"Mat's best overall season ({mat_top_pct}) was in {mat_top_year} and "
        f"Dave's ({dave_top_pct}) was in {dave_top_year}."
    )
    st.plotly_chart(weekly_pct, use_container_width=True)
    st.write("Compare overall winning percentages over the years.")
    st.plotly_chart(win_pct, use_container_width=True)

with tab2:
    st.header("Over/Under")
    st.write(f"Check out the Over/Under picks for {current_year_str}.")
    st.dataframe(df_ou_current, hide_index=True)
    st.plotly_chart(ou_new, use_container_width=True)
    st.plotly_chart(ou_original, use_container_width=True)

with tab3:
    st.header("Teams")
    st.write(cards_text)
    st.plotly_chart(win_pct_cards, use_container_width=True)
    st.write("Here's a table of how the picks have gone for each NFL team.")
    st.dataframe(df_teams_tally, hide_index=True)
    st.plotly_chart(teams_mat, use_container_width=True)
    st.plotly_chart(teams_dad, use_container_width=True)

with tab4:
    st.header("Tallies")
    st.write("Below are the tallies for picks, over/unders, and Cardinals games over the years.")
    st.dataframe(
        total_tally.style.background_gradient(cmap=cm_tally).highlight_null('white'),
        hide_index=True, use_container_width=True
    )

with tab5:
    st.header("Full History")
    st.write("Below is the full history of picks for each week, dating back to 2011.")
    st.dataframe(df_picks.style, hide_index=True)
    st.write("And here are the weekly summaries.")
    st.dataframe(
        df_picks_week12
        .style.format({'Wins': "{:.0f}",'Win Percentage': "{:.3f}"})
        .background_gradient(cmap=cm_wins, subset=['Wins', 'Win Percentage']),
        hide_index=True, use_container_width=True
    )
    st.write("Here's the full history of Over/Unders going back to 2017.")
    st.dataframe(df_ou_full.style, hide_index=True)
