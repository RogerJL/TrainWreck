import matplotlib.pyplot as plt
import pandas as pd
data = pd.read_excel('./data/openDamagesinTrains.xls')
print(data.iloc[1])

#%% Data re-condition
series = data['Damage reporting date']


def convert_dates(df, column):
    dates = df.T.loc[column]

    def convert_date(date_str_or_object):
        if not isinstance(date_str_or_object, str):
            year = date_str_or_object.year
            # month and day are swapped
            month = date_str_or_object.day
            day = date_str_or_object.month
            date_str_or_object = f"{month}/{day}/{year}"
        elif date_str_or_object == "Öppen":
            date_str_or_object = pd.NaT
        return pd.to_datetime(date_str_or_object, format='%m/%d/%Y', exact=True, errors='raise')

    df.loc[:, [column]] = dates.apply(convert_date)

convert_dates(data, 'Damage reporting date')
convert_dates(data, 'Damage closing date')

#%%
print(data.iloc[1])


def extract_damage():
    existing_damages = data['Damage category'].unique()
    ttf = {damage: [] for damage in existing_damages}
    ttr = {damage: [] for damage in existing_damages}
    for vehicle_damage, info in data.groupby(['Vehicle', 'Damage category']):
        # Handling one vehicle and damage category, assume dates in order?
        damage_reporting_date = info['Damage reporting date']
        damage_closing_date = info['Damage closing date']
        damage = vehicle_damage[1]

        time_report_repair = (damage_closing_date - damage_reporting_date) / pd.Timedelta(days=1)
        ttr[damage].extend(time_report_repair)

        first = info[['Damage reporting date']].min().iloc[0]
        no_fault_time = first
        fault_free_period = [(first, first)]
        for issue_report, issue_repair in zip(damage_reporting_date, damage_closing_date):
            if no_fault_time < issue_report:
                fault_free_period.append((no_fault_time, issue_report))
                no_fault_time = issue_repair
            else:
                # so no fault free period, faulty periods connect
                assert issue_report >= fault_free_period[-1][1], "Masking earlier considered fault free"
                if issue_repair >= no_fault_time:
                    no_fault_time = issue_repair
            if pd.isna(issue_repair):
                # there are still unrepaired faults, do not guess
                break
                        
        fault_free_period = fault_free_period[1:]
        
        ttf[damage].extend(map(lambda p: pd.NaT if pd.NaT in p else (p[1] - p[0]) / pd.Timedelta(days=1),
                               fault_free_period[1:]))
    return ttf, ttr

def extract_vehicle():
    existing_vehicles = data['Vehicle'].unique()
    ttf = {vehicle: [] for vehicle in existing_vehicles}
    ttr = {vehicle: [] for vehicle in existing_vehicles}
    for (vehicle,), info in data.groupby(['Vehicle']):
        damage_reporting_date = info['Damage reporting date']  # arrays
        damage_closing_date = info['Damage closing date']  # arrays

        first = info[['Damage reporting date']].min().iloc[0]
        no_fault_time = first
        fault_free_period = [(first, first)]
        for issue_report, issue_repair in zip(damage_reporting_date, damage_closing_date):
            if issue_report > no_fault_time:
                fault_free_period.append((no_fault_time, issue_report))
                no_fault_time = issue_repair
            else:
                # so no fault free period, faulty periods connect
                assert issue_report >= fault_free_period[-1][1], "Masking earler considered fault free"
                if issue_repair >= no_fault_time:
                    no_fault_time = issue_repair
            if pd.isna(issue_repair):
                # there are still unrepaired faults, do not guess
                break

        fault_free_period = fault_free_period[1:]
        
        prev_fault_time = first
        for fault_free in fault_free_period:
            ttf[vehicle].append((fault_free[1] - fault_free[0]) / pd.Timedelta(days=1))
            ttr[vehicle].append((fault_free[0] - prev_fault_time) / pd.Timedelta(days=1))
            prev_fault_time = fault_free[1]
    return ttf, ttr

ttf, ttr = extract_vehicle()

print("Time to failure (ttf)")
for key, times in ttf.items():
    print(f"No Damage {key}: {times}")

ttf = pd.DataFrame.from_dict(ttf, orient='index')
ttr = pd.DataFrame.from_dict(ttr, orient='index')

import matplotlib
import numpy as np
for key in ttf.index:
    ttf.loc[key].hist(bins=50)
    plt.title('Histogram of' + key)
    plt.xlabel('Time to failure (ttf)')
    plt.show()


    ttr.loc[key].hist(bins=50)
    plt.title('Histogram of' + key)
    plt.xlabel('Time to repair (ttr)')
    plt.show()