"""Standalone interactive HTML rendering for the fantasy draft value board."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd


DISPLAY_COLUMNS = [
    "value_board_rank", "player_name", "position", "team", "market_rank", "market_metric",
    "model_rank", "rank_value", "projected_points_q50", "projected_points_q10",
    "projected_points_q90", "beat_market_probability", "bust_probability",
    "risk_adjusted_value_score", "recommendation",
]
NUMERIC_COLUMNS = {
    "value_board_rank", "market_rank", "model_rank", "rank_value", "projected_points_q50",
    "projected_points_q10", "projected_points_q90", "beat_market_probability",
    "bust_probability", "risk_adjusted_value_score",
}


def _render_table(board: pd.DataFrame) -> str:
    display = board[DISPLAY_COLUMNS].copy().round(
        {
            "market_rank": 1, "model_rank": 0, "rank_value": 1,
            "projected_points_q50": 1, "projected_points_q10": 1,
            "projected_points_q90": 1, "beat_market_probability": 3,
            "bust_probability": 3, "risk_adjusted_value_score": 2,
        }
    )
    headers = ['<th class="shortlist-col" data-sortable="false">★</th>']
    for column in DISPLAY_COLUMNS:
        kind = "number" if column in NUMERIC_COLUMNS else "text"
        label = column.replace("_", " ").title()
        headers.append(
            f'<th tabindex="0" role="button" data-column="{escape(column)}" '
            f'data-type="{kind}" aria-sort="none">{escape(label)}<span class="sort-mark"></span></th>'
        )
    rows: list[str] = []
    for _, row in display.iterrows():
        player_key = f'{row["player_name"]}|{row["position"]}'
        cells = [
            f'<td class="shortlist-col"><button class="star" type="button" '
            f'data-player="{escape(player_key, quote=True)}" aria-label="Add {escape(str(row["player_name"]), quote=True)} to shortlist" '
            f'aria-pressed="false">☆</button></td>'
        ]
        for column in DISPLAY_COLUMNS:
            value = "" if pd.isna(row[column]) else str(row[column])
            cells.append(
                f'<td data-column="{escape(column)}" data-value="{escape(value, quote=True)}">{escape(value)}</td>'
            )
        recommendation = str(row["recommendation"]).lower().replace("-", " ").replace(" ", "-")
        rows.append(
            f'<tr data-position="{escape(str(row["position"]), quote=True)}" '
            f'data-recommendation="{escape(str(row["recommendation"]), quote=True)}" '
            f'data-market-rank="{row["market_rank"]}" class="rec-{recommendation}">'
            + "".join(cells) + "</tr>"
        )
    return (
        '<div class="table-wrap"><table class="draft-board" id="draft-board">'
        f'<thead><tr>{"".join(headers)}</tr></thead><tbody>{"".join(rows)}</tbody>'
        '</table></div>'
    )


def write_draft_board_html(board: pd.DataFrame, path: Path) -> Path:
    """Write a portable board with sorting, filters, highlighting, and shortlisting."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = _render_table(board)
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fantasy NFL Draft Value Board</title><style>
:root{{--ink:#17212b;--navy:#15324b;--line:#dce2e8;--panel:#f3f6f8;--accent:#1677a8}}
*{{box-sizing:border-box}} body{{font-family:system-ui,sans-serif;margin:1.5rem;color:var(--ink);background:#fff}}
h1{{margin:0 0 .25rem}} .note{{color:#536270;margin:.25rem 0 1rem}} .controls{{display:flex;flex-wrap:wrap;gap:.75rem;align-items:end;background:var(--panel);padding:1rem;border-radius:.65rem;margin-bottom:.75rem}}
label{{display:grid;gap:.25rem;font-size:.78rem;font-weight:650;color:#44525f}} input,select,button{{font:inherit}} input,select{{padding:.5rem;border:1px solid #aebbc5;border-radius:.35rem;background:white}}
#search{{width:min(25rem,75vw)}} #max-rank{{width:8rem}} .control-button{{padding:.52rem .8rem;border:1px solid #8ca0ae;border-radius:.35rem;background:white;cursor:pointer}}
.control-button:hover,.star:hover{{background:#e7f3f9}} .status{{margin:.6rem 0;color:#536270;font-size:.88rem}}
.table-wrap{{max-height:72vh;overflow:auto;border:1px solid var(--line);border-radius:.5rem}}
table{{border-collapse:separate;border-spacing:0;width:100%;font-size:.84rem;white-space:nowrap}} th,td{{padding:.48rem;border-bottom:1px solid var(--line);text-align:right;background:inherit}}
th{{position:sticky;top:0;z-index:3;background:var(--navy);color:white;cursor:pointer;user-select:none}} th[data-sortable="false"]{{cursor:default}}
th:nth-child(2),td:nth-child(2),th:last-child,td:last-child{{text-align:left}} th:first-child,td:first-child{{position:sticky;left:0;z-index:2}}
th:nth-child(2),td:nth-child(2){{position:sticky;left:2.45rem;z-index:2;box-shadow:2px 0 0 var(--line)}} th:first-child,th:nth-child(2){{z-index:5;background:var(--navy)}}
td:first-child,td:nth-child(2){{background:inherit}} tbody tr:hover{{filter:brightness(.96)}} .sort-mark{{display:inline-block;width:1rem;margin-left:.25rem}}
th[aria-sort="ascending"] .sort-mark::after{{content:"▲"}} th[aria-sort="descending"] .sort-mark::after{{content:"▼"}}
.star{{border:0;background:transparent;color:#9a6a00;font-size:1.2rem;cursor:pointer;padding:0 .25rem}} .star[aria-pressed="true"]{{color:#d09100}}
.rec-strong-value{{background:#dff4e5}} .rec-value{{background:#edf8ee}} .rec-high-risk-upside{{background:#fff4cf}} .rec-overpriced{{background:#fff0e6}} .rec-avoid{{background:#ffe2e2}}
.legend{{display:flex;flex-wrap:wrap;gap:.5rem;margin:.5rem 0 1rem;font-size:.78rem}} .legend span{{padding:.25rem .5rem;border-radius:1rem;border:1px solid var(--line)}}
.shortlist-panel{{display:none;margin:1rem 0;padding:1rem;border:1px solid var(--line);border-radius:.5rem}} .shortlist-panel.active{{display:block}}
.shortlist-panel ul{{columns:2;margin-bottom:0}} @media(max-width:700px){{body{{margin:.75rem}}.shortlist-panel ul{{columns:1}}}}
</style></head><body><h1>Fantasy NFL Draft Value Board</h1>
<p class="note">Click a header to sort. Positive rank value means the model values a player earlier than the market.</p>
<section class="controls" aria-label="Draft board filters">
<label>Search<input id="search" type="search" placeholder="Player, team, position…"></label>
<label>Position<select id="position"><option value="">All positions</option><option>QB</option><option>RB</option><option>WR</option><option>TE</option></select></label>
<label>Recommendation<select id="recommendation"><option value="">All recommendations</option><option>Strong value</option><option>Value</option><option>High-risk upside</option><option>Fair price</option><option>Overpriced</option><option>Avoid</option></select></label>
<label>Maximum market rank<input id="max-rank" type="number" min="1" step="1" placeholder="Any"></label>
<label><span>Shortlist</span><select id="shortlist-filter"><option value="">All players</option><option value="selected">Selected only</option></select></label>
<button id="reset" class="control-button" type="button">Reset</button><button id="show-shortlist" class="control-button" type="button">Compare shortlist</button>
</section>
<div class="legend"><span class="rec-strong-value">Strong value</span><span class="rec-value">Value</span><span class="rec-high-risk-upside">High-risk upside</span><span class="rec-overpriced">Overpriced</span><span class="rec-avoid">Avoid</span></div>
<div id="status" class="status" aria-live="polite"></div><section id="shortlist-panel" class="shortlist-panel"><strong>Shortlisted players</strong><ul id="shortlist-items"></ul></section>
{table}
<script>
const table=document.getElementById('draft-board'), body=table.tBodies[0];
const controls={{search:document.getElementById('search'),position:document.getElementById('position'),recommendation:document.getElementById('recommendation'),maxRank:document.getElementById('max-rank'),shortlist:document.getElementById('shortlist-filter')}};
let selected=new Set(), sortState={{column:'value_board_rank',direction:'ascending'}};
function rows(){{return [...body.rows]}} function value(row,column){{return row.querySelector(`[data-column="${{column}}"]`)?.dataset.value??''}}
function applyFilters(){{const q=controls.search.value.trim().toLowerCase(),max=parseFloat(controls.maxRank.value);let shown=0;rows().forEach(row=>{{const key=row.querySelector('.star').dataset.player;const visible=(!q||row.innerText.toLowerCase().includes(q))&&(!controls.position.value||row.dataset.position===controls.position.value)&&(!controls.recommendation.value||row.dataset.recommendation===controls.recommendation.value)&&(!Number.isFinite(max)||parseFloat(row.dataset.marketRank)<=max)&&(!controls.shortlist.value||selected.has(key));row.hidden=!visible;if(visible)shown++;}});document.getElementById('status').textContent=`Showing ${{shown}} of ${{rows().length}} players · ${{selected.size}} shortlisted`;}}
function sortBy(th){{if(th.dataset.sortable==='false')return;const column=th.dataset.column,direction=sortState.column===column&&sortState.direction==='ascending'?'descending':'ascending',numeric=th.dataset.type==='number',factor=direction==='ascending'?1:-1;rows().sort((a,b)=>{{const av=value(a,column),bv=value(b,column);if(numeric)return((parseFloat(av)||0)-(parseFloat(bv)||0))*factor;return av.localeCompare(bv,undefined,{{numeric:true,sensitivity:'base'}})*factor;}}).forEach(row=>body.appendChild(row));table.querySelectorAll('th[aria-sort]').forEach(h=>h.setAttribute('aria-sort','none'));th.setAttribute('aria-sort',direction);sortState={{column,direction}};applyFilters();}}
table.querySelectorAll('th[data-column]').forEach(th=>{{th.addEventListener('click',()=>sortBy(th));th.addEventListener('keydown',e=>{{if(e.key==='Enter'||e.key===' '){{e.preventDefault();sortBy(th)}}}})}});
Object.values(controls).forEach(control=>control.addEventListener('input',applyFilters));
body.addEventListener('click',event=>{{const star=event.target.closest('.star');if(!star)return;const key=star.dataset.player;if(selected.has(key))selected.delete(key);else selected.add(key);star.textContent=selected.has(key)?'★':'☆';star.setAttribute('aria-pressed',selected.has(key));renderShortlist();applyFilters();}});
function renderShortlist(){{const list=document.getElementById('shortlist-items');list.innerHTML=[...selected].sort().map(key=>`<li>${{key.replace('|',' · ')}}</li>`).join('')||'<li>No players selected</li>';}}
document.getElementById('show-shortlist').addEventListener('click',()=>{{const panel=document.getElementById('shortlist-panel');panel.classList.toggle('active');renderShortlist();}});
document.getElementById('reset').addEventListener('click',()=>{{Object.values(controls).forEach(c=>c.value='');sortBy(table.querySelector('[data-column="value_board_rank"]'));if(sortState.direction==='descending')sortBy(table.querySelector('[data-column="value_board_rank"]'));applyFilters();}});
applyFilters();
</script></body></html>'''
    path.write_text(html, encoding="utf-8")
    return path
