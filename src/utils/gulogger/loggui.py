import PySimpleGUI as sg
import pandas as pd
import json

# query = "'4' in j['record']['extra']['tags']
log_path = 'loguru.log'

f = list(open(log_path, 'r', encoding='utf8', errors="ignore").readlines())
df = list(map(lambda x: json.loads(x), f))

queryinput = sg.InputText('', key='query')
querybtt = sg.Button('Buscar')
table = sg.Table(
    values=[[j['text'], j['record']['extra']['tags']] for j in df],
    headings=['text', 'tags'],
    expand_x=True, expand_y=True,
    justification='left',
    key='table'
)

layout = [
    [sg.Text('Navegador de Logs!')],
    [queryinput, querybtt],
    [table]
]

window = sg.Window('Window Title', layout, resizable=True).Finalize()
window.Maximize()

while True:
    event, values = window.read()

    if event == querybtt.key:
        result = list(filter(lambda j: eval(values[queryinput.key] or 'True'), df))
        table_values = [[j['text'], j['record']['extra']['tags']] for j in result]
        window[table.key].update(
            values=table_values
        )

    if event == sg.WIN_CLOSED or event == 'Cancel':
        break

window.close()
