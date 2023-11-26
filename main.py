import pdfplumber
import csv
import datetime
import os
import requests
from bs4 import BeautifulSoup
import re

# Variables
input_csv_file = 'agenda_items.csv'
output_csv_file = 'cleaned_agenda_items.csv'
# Directory containing PDF files
pdf_directory = 'data/pdfs/'
# List of representatives' names
rep_list = [
    "Watkins", "Adams", "Bewkes", "Boeger", "Campbell", "Dakary-Watkins",
    "Adams", "Baxter", "Berns", "Bewkes", "Boeger", "Campbell", "Coleman", "Cottrell",
    "Curtis", "de-la-Cruz", "Di Costanzo", "Fedeli", "Figueroa", "Garst", "Gilbride",
    "Goldberg", "Grunberger", "Jacobson", "Jean-Louis", "Ley", "Matheny", "Mays",
    "Miller", "Moore", "Morson", "Patterson", "Pavia", "Pierre-Louis",
    "Pollack", "Roqueta", "Saftic", "Sandford", "Shaw", "Shinn", "Sherwood", "Stella",
    "Summerville", "Tomas", "Walston", "David-Watkins", "Weinberg"
]
# empty dictionary to store all attendance records
all_attendance = {}

#User input needed for functions to set timeframe of when to look
start_year_answer = input('What is the start year?')
start_month_answer = input('What is the start month')
start_day_answer = input('What is the start day?')
end_year_answer = input('What is the end year?')
end_month_answer = input('What is the end month?')
end_day_answer = input('What is the end day?')

# The function pull_action_reports()
# pulls all action reports from Weekly Board Communications
# http://www.boardofreps.org/weekly-board-communications.aspx
# Then, because every week ends on a Thursday, loop through every thursday for example: http://boardofreps.org/we231123.aspx
# Would be the week ending 11/23/23. Then it would look for any hyperlinks to pdfs from that page that contain "Action Reports"
def pull_action_reports(start_year, start_month, start_day, end_year, end_month, end_day, ):
    global filename
    week_ending_dates = []

    # Create start and end dates for the year 
    start_date = datetime.date(start_year, start_month, start_day)
    end_date = datetime.date(end_year, end_month, end_day)

    # Iterate through each week from start to end date
    current_date = start_date
    while current_date <= end_date:
        # Format the week-ending date and append to the list
        week_ending_dates.append(current_date.strftime("%m%d"))

        # Move to the next week
        current_date += datetime.timedelta(days=7)

    # week_ending_dates

    websites = []

    # Loop through each week-ending date and construct the URL
    for date in week_ending_dates:
        url = f"http://www.boardofreps.org/we23{date}.aspx"
        try:
            page = requests.get(url)
        except requests.exceptions.RequestException as e:
            print("Error: ", e)
            continue

        soup = BeautifulSoup(page.content, 'html.parser')

        # Find and collect the meeting minutes links
        for a in soup.find_all('a', href=True):
            if "Action Report" in a.text:
                if a['href'].startswith("/Data/"):
                    websites.append("http://www.boardofreps.org" + a['href'])
                elif a['href'].endswith(".pdf"):
                    websites.append(a['href'])
    # Create a directory to store the downloaded files
    if not os.path.exists("data/pdfs/"):
        os.makedirs("data/pdfs/")

    # Loop through each website and saves the pdfs
    for url in websites:
        # Get the filename from the URL
        filename = url.split("/")[-1]

        # Download the PDF file
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            print("Error: ", e)
            continue

        # Save the PDF file to disk
        with open("data/pdfs/" + filename, "wb") as f:
            f.write(response.content)

    return print("Downloaded", filename)


# Function that opens a PDF file and extracts all the text
def read_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text

# Function that takes in raw text and extracts attendance information into a dict with present and absent or excused
def find_attendance(text, file_name):
    # Updated regex pattern to capture the specified excerpt
    pattern = r"(\d+)ROLL CALL: Conducted by Clerk (.+?)\((.*?)\)\."

    # Use re.DOTALL to make dot (.) match newline characters
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)

    attendance_list = []

    for match in matches:
        attendance_text = match.group(3).strip()

        # Replace " were absent or excused" with an empty string
        attendance_text = attendance_text.replace(" were absent or excused", "")

        # Split the attendance text into present and absent/excused parts
        parts = attendance_text.split("were present; ")

        if len(parts) == 2:
            members_present_text, members_absent_or_excused_text = parts
        else:
            members_present_text, members_absent_or_excused_text = attendance_text, ""

        # Clean up and split the text into individual names
        members_present = [name.strip() for name in members_present_text.split(',')]
        members_absent_or_excused = [name.strip() for name in members_absent_or_excused_text.split(',')]

        # Remove 'Reps. ' and 'and ' from each name in the lists
        members_present = [
            name.replace('Reps. ', '').replace('and ', '').replace('were\npresent; ', '').replace(' were present', '')
            for name in members_present]
        members_absent_or_excused = [name.replace('Reps. ', '').replace('and ', '') for name in
                                     members_absent_or_excused]

        # Create a dictionary to represent the attendance record
        attendance_info = {
            "File Name": file_name,
            "Members Present": members_present,
            "Members Absent or Excused": members_absent_or_excused
        }

        # Append the attendance information to the list
        attendance_list.append(attendance_info)

    return attendance_list


def update_attendance_with_user_input(attendance_dict, reps_list):
    updated_attendance = attendance_dict.copy()

    for key in updated_attendance:
        if key in ['Members Present', 'Members Absent or Excused']:
            names_list = updated_attendance[key]
            updated_names_list = []

            for name in names_list:
                # Remove 'Reps. ' if it exists in the name
                cleaned_name = name.replace('Reps. ', '').strip()

                if cleaned_name in reps_list:
                    updated_names_list.append(cleaned_name)
                else:
                    # If the name is not in the reps_list, prompt the user for input
                    print(f"'{cleaned_name}' not found in the reps_list.")
                    action = input(
                        "Do you want to (A)dd, (S)kip, (R)eplace, or (W)rite as two new entries? ").strip().lower()

                    if action == 'a':
                        reps_list.append(cleaned_name)  # Add the name to the reps_list
                        updated_names_list.append(cleaned_name)
                        print(f"'{cleaned_name}' has been added to the reps_list.")
                    elif action == 'r':
                        new_name = input(f"Enter the replacement name for '{cleaned_name}': ").strip()
                        updated_names_list.append(new_name)
                        print(f"'{cleaned_name}' has been replaced with '{new_name}'.")
                    elif action == 'w':
                        new_name1 = input(f"Enter the first new name for '{cleaned_name}': ").strip()
                        new_name2 = input(f"Enter the second new name for '{cleaned_name}': ").strip()
                        updated_names_list.extend([new_name1, new_name2])
                        print(f"'{cleaned_name}' has been written as '{new_name1}' and '{new_name2}'.")
                    else:
                        print(f"'{cleaned_name}' has been skipped.")

            updated_attendance[key] = updated_names_list

    return updated_attendance


# empty dictionary to store all attendance records


def search_pdf_for_pattern(pdf_file):
    patterns = []
    pattern_regex = r'[A-Z]{1,3}31\.[0-9.]{3}'

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            # Search for the pattern using regular expressions
            matches = re.finditer(pattern_regex, text)
            for match in matches:
                pattern = match.group()
                start_index = match.start()
                end_index = match.end()

                # Extract the content between the patterns
                content = text[end_index:]
                next_match = re.search(pattern_regex, content)
                if next_match:
                    content = content[:next_match.start()]

                # Add the pattern and content to the list
                patterns.append({
                    "matched_pattern": pattern,
                    "content": content.strip(),
                    "source": pdf_file
                })

    return patterns



# The function pull_minutes_pdfs() does same thing as action reports but looks for meeting minutes
def pull_minutes_pdfs(start_year_answer, start_month_answer, start_day_answer, end_year_answer, end_month_answer,
                        end_day_answer):
    global filename
    week_ending_dates = []

    # Create start and end dates for the year
    start_date = datetime.date(start_year_answer, start_month_answer, start_day_answer)
    end_date = datetime.date(end_year_answer, end_month_answer, end_day_answer)

    # Iterate through each week from start to end date
    current_date = start_date
    while current_date <= end_date:
        # Format the week-ending date and append to the list
        week_ending_dates.append(current_date.strftime("%m%d"))

        # Move to the next week
        current_date += datetime.timedelta(days=7)

    week_ending_dates

    websites = []

    # Loop through each week-ending date and construct the URL
    for date in week_ending_dates:
        url = f"http://www.boardofreps.org/we23{date}.aspx"
        try:
            page = requests.get(url)
        except requests.exceptions.RequestException as e:
            print("Error: ", e)
            continue

        soup = BeautifulSoup(page.content, 'html.parser')

        # Find and collect the meeting minutes links
        for a in soup.find_all('a', href=True):
            if "Minutes" in a.text:
                if a['href'].startswith("/Data/"):
                    websites.append("http://www.boardofreps.org" + a['href'])
                elif a['href'].endswith(".pdf"):
                    websites.append(a['href'])
    # Create a directory to store the downloaded files
    if not os.path.exists("data/pdfs"):
        os.makedirs("data/pdfs")

    # Loop through each website and saves the pdfs
    for url in websites:
        # Get the filename from the URL
        filename = url.split("/")[-1]

        # Download the PDF file
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            print("Error: ", e)
            continue

        # Save the PDF file to disk
        with open("data/pdfs/" + filename, "wb") as f:
            f.write(response.content)

    return print("Downloaded", filename)




# Asks user whether they want to run the function that pulls all the action reports from January 2023 to now.
pull_action_report_pdfs_answer = input('Do you want to pull all the Action Reports? Please pick thursdays Reply Y or N')
if pull_action_report_pdfs_answer == "Y":
    pull_action_reports(start_year_answer, start_month_answer, start_day_answer, end_year_answer, end_month_answer,
                        end_day_answer)
else:
    print("Alright moving on...")

# Asks user whether they want to run the function that pulls all the meeting minutes from January 2023 to now.
pull_minutes_pdfs_answer = input('Do you want to pull all the Meeting Minutes? Reply Y or N')
if pull_minutes_pdfs_answer == "Y":
    pull_minutes_pdfs(start_year_answer, start_month_answer, start_day_answer, end_year_answer, end_month_answer,
                        end_day_answer)
else:
    print("Alright moving on...")

update_attendance_answer = input('Do you want to redo attendance count? Reply Y or N')
if update_attendance_answer == "Y":
    all_attendance = {}

    for file in os.listdir(pdf_directory):
        if file.endswith('.pdf'):
            pdf_file_path = os.path.join(pdf_directory, file)
            pdf_text = read_pdf(pdf_file_path)
            attendance = find_attendance(pdf_text, file)  # Pass the file name as an argument
            all_attendance[file] = attendance

    # Iterate through all attendance records and update with user input
    for file, attendance in all_attendance.items():
        for item in attendance:
            cleaned_attendance = update_attendance_with_user_input(item, rep_list)
            print(file, cleaned_attendance['Members Absent or Excused'])

    # Directory to store the CSV file
    output_directory = 'output/'

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # File path for the CSV output
    csv_file_path = os.path.join(output_directory, 'attendance_records.csv')

    # Create a CSV file and write the headers
    with open(csv_file_path, 'w', newline='') as csvfile:
        fieldnames = ['File Name', 'Members Present', 'Members Absent or Excused']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write the headers
        writer.writeheader()

        # Iterate through all attendance records and update with user input
        for file, attendance in all_attendance.items():
            for item in attendance:
                cleaned_attendance = update_attendance_with_user_input(item, rep_list)

                # Write the attendance record to the CSV file
                writer.writerow({
                    'File Name': cleaned_attendance['File Name'],
                    'Members Present': ', '.join(cleaned_attendance['Members Present']),
                    'Members Absent or Excused': ', '.join(cleaned_attendance['Members Absent or Excused'])
                })

    print(f"Attendance records saved to {csv_file_path}")
else:
    print("Alright moving on...")

update_agenda_item_answer = input('Do you want to redo agenda item inventory? Reply Y or N')
if update_agenda_item_answer == 'Y':
    agenda_items = []
    for file in os.listdir(pdf_directory):
        if file.endswith('.pdf'):
            pdf_file_path = os.path.join(pdf_directory, file)
            agenda_items.extend(search_pdf_for_pattern(pdf_file_path))  # Use extend to add elements to the list

    # Specify the output CSV file path
    output_csv_file = 'agenda_items.csv'

    # Write the agenda items to the CSV file
    with open(output_csv_file, 'w', newline='') as csvfile:
        fieldnames = ['matched_pattern', 'content', 'source']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write the CSV header
        writer.writeheader()

        # Write each agenda item as a row in the CSV file
        for item in agenda_items:
            writer.writerow(item)

    print(f'Agenda items saved to {output_csv_file}')
else:
    print("Alright moving on...")


def extract_motion_info(content):
    # Define a pattern to find "A motion to" followed by text until a sentence ending with period and newline
    pattern = r'A motion to(.*?[.]\n)'

    # Search for the pattern
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)

    # Initialize motion_info as an empty string
    motion_info = ""

    if match:
        motion_info = match.group(1).strip()

    return motion_info


def clean_agenda_items(input_csv_file, output_csv_file):
    # Read the input CSV file
    agenda_items = []
    with open(input_csv_file, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            agenda_items.append(row)

    # Define field names including the new "date" and "committee code" fields
    fieldnames = list(agenda_items[0].keys()) + ['date', 'committee code', 'motion_info']

    # Process each agenda item and add the "date" and "committee code" fields
    for item in agenda_items:
        source = item['source']
        date = source.split('/')[-1].split('.')[0][-4:]  # Extract the date as the last 4 digits before ".pdf"
        item['date'] = date

        matched_pattern = item['matched_pattern']
        committee_code = re.search(r'^[A-Z]+', matched_pattern)
        if committee_code:
            committee_code = committee_code.group()
        else:
            committee_code = ''
        item['committee code'] = committee_code

        content = item['content']
        motion_info = extract_motion_info(content)
        item['motion_info'] = motion_info

    # Write the updated agenda items to the output CSV file
    with open(output_csv_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write the CSV header
        writer.writeheader()

        # Write each item to the CSV file
        for item in agenda_items:
            writer.writerow(item)

    print(f'Cleaned agenda items saved to {output_csv_file}')


clean_agenda_items_answer = input('Do you want to clean the agenda items? Reply Y or N')
if clean_agenda_items_answer == "Y":
    clean_agenda_items(input_csv_file, output_csv_file)
else:
    print("Alright moving on...")
