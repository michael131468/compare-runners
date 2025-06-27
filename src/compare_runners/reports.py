from pathlib import Path

from tabulate import tabulate

def make_html_table(runner_stats: dict) -> Path:
    # TODO: Rework to ensure ordering of runners is consistent (ordered dicts
    # give us this by chance but it should be made more explicit)
    # TODO: Add quick contents links to top of page for users to see overview
    # and jump to tables quickly
    html_top = """<html>
<head>
    <!-- Thanks to https://dev.to/dcodeyt/creating-beautiful-html-tables-with-css-428l -->
    <style>
        h1 {
            font-family: sans-serif;
        }

        table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            font-family: sans-serif;
            min-width: 400px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
        }

        table thead tr {
            background-color: #009879;
            color: #ffffff;
            text-align: left;
        }

        table th,
        table td {
            padding: 12px 15px;
        }

        table tbody tr {
            border-bottom: 1px solid #dddddd;
        }

        table tbody tr:nth-of-type(even) {
            background-color: #f3f3f3;
        }

        table tbody tr:last-of-type {
            border-bottom: 2px solid #009879;
        }
        table tbody tr.active-row {
            font-weight: bold;
            color: #009879;
        }
    </style>
</head>
<body>"""
    html_bottom = """</body>
</html>"""
    html = html_top

    for repo in runner_stats:
        table_avg_total = []
        table_avg_queue = []
        table_avg_runtime = []

        # Determine headers
        headers = ["Job"]
        for job in runner_stats[repo]:
            for runner in runner_stats[repo][job]:
                headers.append(runner)
            break

        for job in runner_stats[repo]:
            table_avg_total_row = [job]
            table_avg_queue_row = [job]
            table_avg_runtime_row = [job]
            for runner in runner_stats[repo][job]:
                table_avg_total_row.append(runner_stats[repo][job][runner]["total_duration_avg"])
                table_avg_queue_row.append(runner_stats[repo][job][runner]["queue_duration_avg"])
                table_avg_runtime_row.append(runner_stats[repo][job][runner]["runtime_duration_avg"])
            table_avg_total.append(table_avg_total_row)
            table_avg_queue.append(table_avg_queue_row)
            table_avg_runtime.append(table_avg_runtime_row)
        html += f"<h1>{repo} (Average Total Duration aka Run Time + Queue Time)</h1>"
        html += tabulate(table_avg_total, headers=headers, floatfmt=".2f", tablefmt="html")
        html += f"<h1>{repo} (Average Queue Time)</h1>"
        html += tabulate(table_avg_queue, headers=headers, floatfmt=".2f", tablefmt="html")
        html += f"<h1>{repo} (Average Run Time)</h1>"
        html += tabulate(table_avg_runtime, headers=headers, floatfmt=".2f", tablefmt="html")
    html += html_bottom
    with open("./runner_statistics.html", "w") as f:
        f.write(html)
    return Path("./runner_statistics.html")