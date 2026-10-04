import pandas as pd

def monthly_forecast(pnl, months=6):
    rows=[]
    for cat,g in pnl.groupby('category'):
        g=g.groupby('month',as_index=False)['actual'].sum().sort_values('month')
        base=g.actual.tail(3).mean() if len(g) else 0
        last=g.month.max() if len(g) else pd.Timestamp.today().replace(day=1)
        for i in range(1,months+1):
            rows.append({'month':last+pd.offsets.MonthBegin(i),'category':cat,'forecast':base})
    return pd.DataFrame(rows)
