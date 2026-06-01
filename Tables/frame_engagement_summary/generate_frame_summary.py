import pandas as pd
import numpy as np

# Read dataset
input_csv = "Datasets/final_dataset.csv"
df = pd.read_csv(input_csv)

# Parse numeric columns
def parse_numeric(x):
    if isinstance(x, str):
        return float(x.replace(",", ""))
    return float(x)

df['view_count'] = df['view_count'].apply(parse_numeric)
df['comment_count'] = df['comment_count'].apply(parse_numeric)
df['video_like_count'] = df['video_like_count'].apply(parse_numeric)

# Remove rows with missing frame or engagement data
df = df.dropna(subset=['frame', 'view_count', 'comment_count', 'video_like_count'])
df['frame'] = df['frame'].str.strip()

# Calculate statistics by frame
stats = []
for frame in sorted(df['frame'].unique()):
    frame_data = df[df['frame'] == frame]
    
    stats.append({
        'Frame': frame,
        'Total N': len(frame_data),
        'Total Views': int(frame_data['view_count'].sum()),
        'Mean Views': frame_data['view_count'].mean(),
        'Median Views': frame_data['view_count'].median(),
        'Total Likes': int(frame_data['video_like_count'].sum()),
        'Mean Likes': frame_data['video_like_count'].mean(),
        'Median Likes': frame_data['video_like_count'].median(),
        'Total Comments': int(frame_data['comment_count'].sum()),
        'Mean Comments': frame_data['comment_count'].mean(),
        'Median Comments': frame_data['comment_count'].median(),
    })

stats_df = pd.DataFrame(stats)

label_map = {
    "Climate Change and Natural Disaster": "Climate Change",
    "Climate change and Natural Disaster": "Climate Change",
    "Climate change and natural disaster": "Climate Change",
    "Geopolitical and Strategic": "Geopolitics",
    "Knowledge and Education": "Knowledge/Facts",
    "Local Cultures and Everyday life": "Indigenous Life",
    "Nature and Tourism": "Nature/Tourism",
}

def frame_label(x):
    return label_map.get(x, x)

def format_value(x):
    return f"{int(round(x)):,}"

# Generate HTML with frames as columns
html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Frame Engagement Summary</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #ffffff;
            color: #000000;
        }
        h1 {
            color: #000000;
        }
        table {
            border-collapse: collapse;
            background-color: #ffffff;
            color: #000000;
            width: 100%;
        }
        th {
            background-color: #f2f2f2;
            color: #000000;
            padding: 12px;
            text-align: center;
            font-weight: bold;
            border: 1px solid #cccccc;
        }
        td {
            padding: 10px 12px;
            border: 1px solid #cccccc;
            background-color: #ffffff;
            color: #000000;
        }
        td.group-label {
            font-weight: 700;
            text-align: left;
            vertical-align: middle;
        }
        td.metric {
            font-weight: 600;
            text-align: left;
        }
        td.numeric {
            text-align: right;
        }
        tr.section-border td {
            border-bottom: 3px solid #000000;
        }
        tr:hover td:not(.metric):not(.group-label) {
            background-color: #ffffff;
        }
        th:first-child {
            text-align: left;
        }
    </style>
</head>
<body>
    <h1>Frame Engagement Summary Statistics</h1>
    <p>Summary of engagement metrics (views, likes, comments) by content frame.</p>
    <table>
        <thead>
            <tr>
                <th colspan="2">Metric</th>
"""

# Header row with frame names
for _, row in stats_df.iterrows():
    html_content += f"                <th>{frame_label(row['Frame'])}</th>\n"

html_content += """            </tr>
        </thead>
        <tbody>
"""

# N Videos row
html_content += "            <tr>\n                <td class=\"metric\" colspan=\"2\">N Videos</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Total N'])}</td>\n"
html_content += "            </tr>\n"

# Views section
html_content += "            <tr>\n                <td class=\"group-label\" rowspan=\"3\">Views</td>\n                <td class=\"metric\">Total</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Total Views'])}</td>\n"
html_content += "            </tr>\n"

html_content += "            <tr>\n                <td class=\"metric\">Mean</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Mean Views'])}</td>\n"
html_content += "            </tr>\n"

html_content += "            <tr class=\"section-border\">\n                <td class=\"metric\">Median</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Median Views'])}</td>\n"
html_content += "            </tr>\n"

# Likes section
html_content += "            <tr>\n                <td class=\"group-label\" rowspan=\"3\">Likes</td>\n                <td class=\"metric\">Total</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Total Likes'])}</td>\n"
html_content += "            </tr>\n"

html_content += "            <tr>\n                <td class=\"metric\">Mean</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Mean Likes'])}</td>\n"
html_content += "            </tr>\n"

html_content += "            <tr class=\"section-border\">\n                <td class=\"metric\">Median</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Median Likes'])}</td>\n"
html_content += "            </tr>\n"

# Comments section
html_content += "            <tr>\n                <td class=\"group-label\" rowspan=\"3\">Comments</td>\n                <td class=\"metric\">Total</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Total Comments'])}</td>\n"
html_content += "            </tr>\n"

html_content += "            <tr>\n                <td class=\"metric\">Mean</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Mean Comments'])}</td>\n"
html_content += "            </tr>\n"

html_content += "            <tr class=\"section-border\">\n                <td class=\"metric\">Median</td>\n"
for _, row in stats_df.iterrows():
    html_content += f"                <td class=\"numeric\">{format_value(row['Median Comments'])}</td>\n"
html_content += "            </tr>\n"

html_content += """        </tbody>
    </table>
</body>
</html>
"""

# Write to file
output_path = "Analysis/frame_engagement_summary/frame-engagement-summary-table.html"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Saved summary table to: {output_path}")
print(f"\nFrame summary statistics:")
print(stats_df.to_string(index=False))
