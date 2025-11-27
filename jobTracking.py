import marimo

__generated_with = "0.14.11"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import os
    import json
    import marimo as mo
    import pandas as pd
    import numpy as np
    import dayplot as dp
    import matplotlib.pyplot as plt
    from datetime import date, timedelta, datetime

    # Reactive state variable to act as a refresh trigger
    data_refresh_trigger, set_refresh_trigger = mo.state(0)
    image_refresh_trigger, set_image_refresh_trigger = mo.state(0)

    # Define the controlled list for 'type'
    type_options = [
        'Application',
        'Rejection',
        'Interest',
        'Recruiter',
        'Interview',
        'Offer'
    ]

    def check_file(filepath):
        """
        Checks if a file exists. If it doesn't, create an empty file.
    
        Args:
            filepath (str): The full path and filename to check/create.
        """
        if not os.path.exists(filepath):
            try:
                # Use 'w' mode to create the file
                with open(filepath, 'w') as f:
                    # Create an empty file
                    pass
                print(f"{filepath} created successfully")
                return True
            except IOError as e:
                print(f"Error creating file {filepath}: {e}")
                return False
        else:
            print(f"{filepath} found.")
            return True

    # Define the file path and check it exists for new instances
    file_path = "tracking.json"
    if check_file(file_path):
        mo.md("Tracking file found or created.")
    else:
        mo.md(f"Unable to create {file_path}.")
    return (
        data_refresh_trigger,
        date,
        datetime,
        dp,
        file_path,
        image_refresh_trigger,
        json,
        mo,
        pd,
        plt,
        set_refresh_trigger,
        timedelta,
        type_options,
    )


@app.cell(hide_code=True)
def _(data_refresh_trigger, datetime, pd, timedelta):
    def get_data(trigger_value):
        # Get the data and split it out into the required df's
        df_all = pd.read_json("tracking.json")
        df_apps = df_all.copy()
        df_others = df_apps.copy()
        df_rej = df_apps.copy()

        # Filter the df's to get the correct dataset
        df_apps = df_apps[df_apps["type"] == "Application"].reset_index()
        df_rej = df_rej[df_rej["type"] == "Rejection"].reset_index()
        df_rej['has_rejection'] = True
        df_others = df_others[df_others["type"] != "Application"]

        # Correction to the date, getting just the date and note time
        df_apps['date'] = df_apps['date'].dt.strftime('%Y-%m-%d')

        # Get the latest updates for each application
        df_others = df_others.sort_values(by='date', ascending=False)
        df_others = df_others.drop_duplicates(subset=['company', 'job_title'], keep='first')
        df_others.rename(columns={"date": "last_updated", "notes": "latest_notes"}, inplace=True)
        df_others['stage'] = df_others['type']

        # Update the dataset to the correct format for merging
        df_others = df_others[['company', 'job_title', 'last_updated', 'stage', 'latest_notes']]
        df_others['last_updated'] = df_others['last_updated'].dt.strftime('%Y-%m-%d')

        # Merge the datasets to get recorded rejections
        df_apps = df_apps.merge(
            df_rej[['company', 'job_title', 'has_rejection']],
            on = ['company', 'job_title'],
            how = 'left'
        )

        # Merge the datasets to get the latest update dates and notes
        df_apps = df_apps.merge(
            df_others,
            on = ['company', 'job_title'],
            how = 'left'
        )

        # Fill in any empty cells with the application date
        df_apps['last_updated'] = df_apps.apply(
            lambda x: x['date'] if pd.isna(x['last_updated']) else x['last_updated'],
            axis = 1
        )

        # Fill in the blanks with false for the rejections
        df_apps['has_rejection'] = df_apps['has_rejection'].apply(lambda x: x if x == True else False)

        # Calculate if a rejection is assumed. This should be 3 week after the last update
        df_apps['has_assumed_rejection'] = df_apps.apply(
            lambda x: True if datetime.strptime(x['last_updated'], '%Y-%m-%d') + timedelta(days=21) < datetime.today() else False, axis=1
        )

        # Combine the rejection and assumed rejection columns
        df_apps['is_rejected'] = df_apps.apply(
            lambda x: True if x['has_rejection'] == True or x['has_assumed_rejection'] == True else False,
            axis=1
        )

        def get_latest_update(row):
            """Gets the latest notes from the application notes, latest notes or adding in a custom note if it's an assumed rejection."""
            if pd.isna(row['latest_notes']) and row['is_rejected']:
                return "Assumed rejection as past 3 week."
            elif pd.isna(row['latest_notes']):
                return row['notes']
            else:
                return row['latest_notes']
        df_apps['latest_notes'] = df_apps.apply(
            get_latest_update,
            axis = 1
        )

        def set_stage(row):
            """Change up the stage based on the note."""
            if row['is_rejected'] == True:
                return 'Rejection'
            elif pd.isna(row['stage']):
                return 'Application'
            else:
                return row['stage']
        df_apps['stage'] = df_apps.apply(set_stage, axis=1)

        return df_all, df_apps, df_others, df_rej

    df_all, df_apps, df_others, df_rej = get_data(data_refresh_trigger)
    return df_all, df_apps, df_others


@app.cell
def _(mo):
    mo.md(
        r"""
    <h1 style="
        margin-top: 0; 
        margin-bottom: 10px; 
        font-size: 4em; 
        color: #333;
        font-family: Arial, Helvetica, sans-serif;
    ">
        Job Tracking
    </h1>
    """
    )
    return


@app.cell
def _(date, datetime, file_path, json, mo, set_refresh_trigger, type_options):
    # --- UI Elements ---

    # Input for 'type' (Dropdown)
    type_input = mo.ui.dropdown(
        type_options,
        label="Type",
        value=type_options[0] # Default to 'Application'
    )

    # Input for 'date' (Date Picker)
    date_input = mo.ui.date(
        label="Date",
        value=date.today().isoformat() # Default to today's date
    )

    # Input for 'company' (Text)
    company_input = mo.ui.text(
        label="Company",
        value=""
    )

    # Input for 'job_title' (Text)
    job_title_input = mo.ui.text(
        label="Job Title (Use 'NA' if not applicable)",
        value=""
    )

    # Input for 'notes' (Text Area)
    notes_input = mo.ui.text_area(
        label="Notes",
        value="",
        full_width=True
    )


    def save_new_object(e):
        """
        Function to handle the button click and save the new object to the file.
        """  
        data = None

        try:
            # Read the existing file
            with open(file_path, 'r') as file:
                # Load the JSON data into a Python list
                data = json.load(file)

            if data is None:
                raise Exception("Data not read correctly.")

            # Add the new input to the existing list
            new_object = {
                "type": type_input.value,
                "date": datetime.strftime(date_input.value, '%Y-%m-%d'),
                "company": company_input.value,
                "job_title": job_title_input.value,
                "notes": notes_input.value
            }
            data.append(new_object)

            # Open the file again in write mode to overwrite the content
            with open(file_path, 'w') as file:
                # Dump the updated Python list back into the file
                # Use indent=4 for clean, readable formatting
                json.dump(data, file, indent=4)

            # ⭐ NEW: Increment the trigger to force get_data() to re-run!
            set_refresh_trigger(lambda value: value + 1)

        except IOError:
            # Escape if error
            pass;


    # Save Button
    save_button = mo.ui.button(
        label="✨ Add New Entry",
        on_click=save_new_object,
        kind="success",
    )

    form_elements_top = mo.hstack([
        type_input,
        date_input,
        company_input,
        job_title_input,
    ])

    form_elements = mo.vstack([
        form_elements_top,
        notes_input
    ])

    # Use CSS Grid to arrange the form elements uniformly
    # Note: notes_input is explicitly set to span 2 columns below for better layout.
    mo.md(f"""
        <h3 style="
            margin-top: 0; 
            margin-bottom: 10px; 
            font-size: 2em; 
            color: #333;
            font-family: Arial, Helvetica, sans-serif;
        ">
            Add New Tracking Entry
        </h3>
        <div style="
            width: 100%
            display: grid;
            grid-template-columns: 1fr 1fr; /* Two equal columns */
            gap: 15px; /* Spacing between elements */
            padding: 10px;
            border: 1px solid #ccc; /* Optional: border to visually group the form */
            border-radius: 8px;
        ">
            {form_elements}
        </div>
        <div style="margin-top: 15px;">
            {mo.as_html(save_button)}
        </div>
    """)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    <h2 style="
        margin-top: 0; 
        margin-bottom: 10px; 
        font-size: 2.75em; 
        color: #333;
        font-family: Arial, Helvetica, sans-serif;
    ">
        Last 2 Week
    </h2>
    """
    )
    return


@app.cell
def _(datetime, df_apps, mo, timedelta):
    two_week_date = datetime.today() - timedelta(days=21);
    two_week_apps = df_apps[df_apps['date'] > datetime.strftime(two_week_date, '%Y-%m-%d')]['stage'].count();
    two_week = 2;

    mo.md(
        f"""
        <div style="display: inline-flex; justify-content: space-around; width: 100%; font-family: sans-serif;">

            <div style="
                flex: 1; 
                padding: 20px; 
                margin: 0 10px; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                text-align: center; 
                background-color: #f9f9f9;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <h3 style="
                    margin-top: 0; 
                    margin-bottom: 10px; 
                    font-size: 2em; 
                    color: #333;
                    font-family: Arial, Helvetica, sans-serif;
                ">
                    Applications
                </h3>
                <div style="font-size: 3em; font-weight: bold; color: #007bff; display: inline-block;">
                    {two_week_apps}
                </div>
                <span style="font-size: 0.9em; color: #666; margin-left: 5px;">
                    apps
                </span>
            </div>

            <div style="
                flex: 1; 
                padding: 20px; 
                margin: 0 10px; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                text-align: center; 
                background-color: #f9f9f9;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <h3 style="
                    margin-top: 0; 
                    margin-bottom: 10px; 
                    font-size: 2em; 
                    color: #333;
                    font-family: Arial, Helvetica, sans-serif;
                ">
                    Application rate
                </h3>
                <div style="font-size: 3em; font-weight: bold; color: #ffc107; display: inline-block;">
                    {two_week_apps / two_week:.2f}
                </div>
                <span style="font-size: 0.9em; color: #666; margin-left: 5px;">
                    jobs/wk
                </span>
            </div>

        </div>
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    <h2 style="
        margin-top: 0; 
        margin-bottom: 10px; 
        font-size: 2.75em; 
        color: #333;
        font-family: Arial, Helvetica, sans-serif;
    ">
        Overall
    </h2>
    """
    )
    return


@app.cell
def _(datetime, df_apps, mo):
    total = df_apps['stage'].count();
    first_day = datetime.strptime(df_apps.sort_values('date', ascending=True)['date'][0], '%Y-%m-%d')
    weeks_looking = (datetime.today() - first_day).days / 7

    mo.md(
        f"""
        <div style="display: inline-flex; justify-content: space-around; width: 100%; font-family: sans-serif;">

            <div style="
                flex: 1; 
                padding: 20px; 
                margin: 0 10px; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                text-align: center; 
                background-color: #f9f9f9;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <h3 style="
                    margin-top: 0; 
                    margin-bottom: 10px; 
                    font-size: 2em; 
                    color: #333;
                    font-family: Arial, Helvetica, sans-serif;
                ">
                    Applications
                </h3>
                <div style="font-size: 3em; font-weight: bold; color: #007bff; display: inline-block;">
                    {total}
                </div>
                <span style="font-size: 0.9em; color: #666; margin-left: 5px;">
                    apps
                </span>
            </div>

            <div style="
                flex: 1; 
                padding: 20px; 
                margin: 0 10px; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                text-align: center; 
                background-color: #f9f9f9;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <h3 style="
                    margin-top: 0; 
                    margin-bottom: 10px; 
                    font-size: 2em; 
                    color: #333;
                    font-family: Arial, Helvetica, sans-serif;
                ">
                    Weeks Looking
                </h3>
                <div style="font-size: 3em; font-weight: bold; color: #28a745; display: inline-block;">
                    {weeks_looking:.0f}
                </div>
                <span style="font-size: 0.9em; color: #666; margin-left: 5px;">
                    weeks
                </span>
            </div>

            <div style="
                flex: 1; 
                padding: 20px; 
                margin: 0 10px; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                text-align: center; 
                background-color: #f9f9f9;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <h3 style="
                    margin-top: 0; 
                    margin-bottom: 10px; 
                    font-size: 2em; 
                    color: #333;
                    font-family: Arial, Helvetica, sans-serif;
                ">
                    Application rate
                </h3>
                <div style="font-size: 3em; font-weight: bold; color: #ffc107; display: inline-block;">
                    {total / weeks_looking:.2f}
                </div>
                <span style="font-size: 0.9em; color: #666; margin-left: 5px;">
                    jobs/wk
                </span>
            </div>

        </div>
        """
    )
    return


@app.cell
def _(df_apps, mo):
    live = df_apps[df_apps['stage'] != 'Rejection']['stage'].count();

    mo.md(
      f"""
        <div style="
            flex: 1; 
            padding: 20px; 
            margin: 0 10px; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            text-align: center; 
            background-color: #f9f9f9;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        ">
            <h3 style="
                margin-top: 0; 
                margin-bottom: 10px; 
                font-size: 2em; 
                color: #333;
                font-family: Arial, Helvetica, sans-serif;
            ">
                Live Applications
            </h3>
            <div style="font-size: 3em; font-weight: bold; color: #ff0000; display: inline-block;">
                {live}
            </div>
        </div>
      """
    )
    return


@app.cell
def _(df_apps):
    df_apps[df_apps['stage'] != 'Rejection'][['last_updated', 'company', 'job_title', 'stage', 'latest_notes']].sort_values('last_updated', ascending=False).reset_index(drop=True)
    return


@app.cell
def _(mo):
    mo.md(
        """
    <h1 style="
        margin-top: 0; 
        margin-bottom: 10px; 
        font-size: 4em; 
        color: #333;
        font-family: Arial, Helvetica, sans-serif;
    ">
        Applications
    </h1>
    """
    )
    return


@app.cell
def _(df_apps, pd):
    df_apps2 = df_apps.copy()

    df_apps2['date'] = pd.to_datetime(df_apps2['date'])
    df_apps2 = df_apps2['date'].value_counts().sort_index()
    print(type(df_apps2.index[0]))
    return (df_apps2,)


@app.cell
def _(datetime, df_apps, df_apps2, dp, image_refresh_trigger, pd, plt):
    def plot_applications(trigger):

        # Create a dataframe showing only applications and count them
        df2 = df_apps.copy()
        df2['date'] = pd.to_datetime(df2['date'])
        df2 = df2['date'].value_counts().sort_index()

        # Create a heatmap
        fig, ax = plt.subplots(figsize=(15, 6), dpi=300)
        ax.set_title("Applications")
        dp.calendar(
            dates=df2.index,
            values=df2.values,
            cmap="Wistia",
            legend=True,
            start_date=df_apps2.index[0],
            end_date=datetime.today(),
            boxstyle="circle",
            color_for_none="ghostwhite",
            ax=ax,
        )
        return plt

    app_plt = plot_applications(image_refresh_trigger)
    app_plt.gca()
    return


@app.cell
def _(mo):
    # Create the textbox UI element
    company_search = mo.ui.text(
        label="Company search:",
        placeholder="company name...",
    )

    # Display the UI element
    company_search
    return (company_search,)


@app.cell
def _(mo):
    # Create the textbox UI element
    job_search = mo.ui.text(
        label="Job search:",
        placeholder="Job name...",
    )

    # Display the UI element
    job_search
    return (job_search,)


@app.cell
def _(company_search, df_apps, job_search):
    company = company_search.value
    job = job_search.value

    df_apps[df_apps['company'].str.contains(company, case=False) & df_apps['job_title'].str.contains(job, case=False)][['date', 'last_updated', 'company', 'job_title', 'stage', 'latest_notes']].sort_values('last_updated', ascending=False).reset_index(drop=True)
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    <h1 style="
        margin-top: 0; 
        margin-bottom: 10px; 
        font-size: 4em; 
        color: #333;
        font-family: Arial, Helvetica, sans-serif;
    ">
        Interviews
    </h1>
    """
    )
    return


@app.cell
def _(df_apps, mo):
    at_interview = df_apps[df_apps['stage'] == 'Interview']['stage'].count();

    mo.md(
      f"""
        <div style="
            flex: 1; 
            padding: 20px; 
            margin: 0 10px; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            text-align: center; 
            background-color: #f9f9f9;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        ">
            <h3 style="
                margin-top: 0; 
                margin-bottom: 10px; 
                font-size: 2em; 
                color: #333;
                font-family: Arial, Helvetica, sans-serif;
            ">
                At Interview Stage
            </h3>
            <div style="font-size: 3em; font-weight: bold; color: #0044ff; display: inline-block;">
                {at_interview}
            </div>
        </div>
      """
    )
    return


@app.cell
def _(df_apps):
    df_apps[df_apps['stage'] == 'Interview'][['last_updated', 'company', 'job_title', 'stage', 'latest_notes']].reset_index(drop=True)
    return


@app.cell
def _(datetime, df_all, dp, image_refresh_trigger, pd, plt):
    def plot_interview_dates(trigger):
        # Create a dataframe showing only interviews and count them
        df3 = df_all[df_all["type"] == "Interview"].copy()
        df3['date'] = pd.to_datetime(df3['date'])
        df3 = df3['date'].value_counts().sort_index()

        # Create a heatmap
        fig2, ax2 = plt.subplots(figsize=(15, 6), dpi=300)
        ax2.set_title("Interviews")
        dp.calendar(
            dates=df3.index,
            values=df3.values,
            cmap="Wistia",
            legend=True,
            start_date=df3.index[0],
            end_date= df3.index[0] if df3.index[0] > datetime.today() else datetime.today(),
            boxstyle="circle",
            color_for_none="ghostwhite",
            ax=ax2,
        )

        return plt

    plt_interviews = plot_interview_dates(image_refresh_trigger)
    plt_interviews.gca()
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    <h1 style="
        margin-top: 0; 
        margin-bottom: 10px; 
        font-size: 4em; 
        color: #333;
        font-family: Arial, Helvetica, sans-serif;
    ">
        Interest and Recruitment
    </h1>
    """
    )
    return


@app.cell
def _(df_others):
    df_others[(df_others['stage'] == 'Recruiter') | (df_others['stage'] == 'Interest')][['stage', 'company','latest_notes', 'last_updated']].reset_index(drop=True)
    return


if __name__ == "__main__":
    app.run()
