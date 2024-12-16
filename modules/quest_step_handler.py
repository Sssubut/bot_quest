import openpyxl
import csv


def save_quest(excel_file, quest_id):
    wb = openpyxl.load_workbook(excel_file)
    sheet = wb.worksheets[0]

    with open(f'data/quests/{quest_id}.csv', 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=';')

        for row in sheet.iter_rows(values_only=True):
            csv_writer.writerow(row)


def load_quest(quest_id):
    with open(f'data/quests/{quest_id}.csv', 'r', newline='', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=';')

        # return как массив из массивов
        return [row for row in csv_reader][1:]

