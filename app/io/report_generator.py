from pathlib import Path
from typing import Any

def generate_html_report(data: dict[str, Any], output_path: str) -> str:
    """Generates a premium, modern HTML dashboard for the BIM Audit."""
    
    audit = data.get("bim_quality_audit", {})
    score_str = audit.get("completeness_score", "0%")
    # Strip % and handle empty values
    try:
        score_val = float(score_str.replace("%", ""))
    except Exception:
        score_val = 0.0
        
    report_text = audit.get("detailed_report", "No report available.")
    
    model_name = data.get("file_name", "BIM Model")
    elements = data.get("data", {})
    walls = elements.get("walls", [])
    slabs = elements.get("slabs", [])
    
    # Identify missing data for the report
    missing_items = []
    for w in walls:
        if not w.get("fire_rating"):
            missing_items.append({"id": w.get("guid"), "category": "Wall", "issue": "Missing Fire Rating"})
        if not w.get("material"):
            missing_items.append({"id": w.get("guid"), "category": "Wall", "issue": "Missing Material"})
            
    # Premium CSS & HTML Template
    color = '#38bdf8' if score_val > 80 else '#fbbf24' if score_val > 50 else '#f43f5e'
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BIM Audit: {model_name}</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #0f172a;
                --card-bg: #1e293b;
                --primary: #38bdf8;
                --accent: #f43f5e;
                --text: #f1f5f9;
                --text-dim: #94a3b8;
                --score-color: {color};
            }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg);
                color: var(--text);
                line-height: 1.6;
                padding: 40px;
            }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            header {{ margin-bottom: 40px; border-bottom: 1px solid #334155; padding-bottom: 20px; }}
            h1 {{ font-size: 2.5rem; font-weight: 600; color: var(--primary); }}
            .model-info {{ color: var(--text-dim); margin-top: 5px; font-size: 0.9rem; }}
            
            .dashboard {{ display: grid; grid-template-columns: 1fr; gap: 30px; margin-bottom: 40px; }}
            
            .card {{ background: var(--card-bg); border-radius: 16px; padding: 30px; border: 1px solid #334155; }}
            
            .ai-report {{ font-style: italic; white-space: pre-wrap; color: #cbd5e1; font-size: 0.95rem; }}
            
            h2 {{ font-size: 1rem; margin-bottom: 20px; color: var(--primary); text-transform: uppercase; letter-spacing: 1px; }}
            
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ text-align: left; color: var(--text-dim); text-transform: uppercase; font-size: 0.7rem; padding: 10px; border-bottom: 1px solid #334155; }}
            td {{ padding: 10px; font-size: 0.85rem; border-bottom: 1px solid #1e293b; color: #cbd5e1; }}
            .badge {{ background: #f43f5e22; color: #f43f5e; padding: 4px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 600; }}
            
            .footer {{ margin-top: 60px; text-align: center; color: var(--text-dim); font-size: 0.8rem; opacity: 0.5; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>BIM Data Quality Audit</h1>
                <p class="model-info">Target Model: {model_name} • Elements Processed: {len(walls) + len(slabs)}</p>
            </header>
            
            <div class="dashboard">
                <div class="card">
                    <h2>Expert AI Risk Analysis</h2>
                    <div class="ai-report">{report_text}</div>
                </div>
            </div>
            
            <div class="card" style="margin-top: 30px;">
                <h2>Missing Metadata Exceptions</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th>Global ID</th>
                            <th>Issue Flag</th>
                        </tr>
                    </thead>
                    <tbody>
                        {" ".join([f"<tr><td>{i['category']}</td><td style='font-family: monospace;'>{i['id']}</td><td><span class='badge'>{i['issue']}</span></td></tr>" for i in missing_items[:30]])}
                        { "<tr><td colspan='3' style='text-align:center; padding: 20px;'>... audit truncated for report readability</td></tr>" if len(missing_items) > 30 else "" }
                        { "<tr><td colspan='3' style='text-align:center;'>No critical metadata issues found.</td></tr>" if not missing_items else "" }
                    </tbody>
                </table>
            </div>

            <div class="footer">
                Antigravity BIM Auditing Suite • (c) 2026 
            </div>
        </div>
    </body>
    </html>
    """
    
    report_path = Path(output_path).with_suffix(".html")
    report_path.write_text(html_template, encoding="utf-8")
    return str(report_path)
