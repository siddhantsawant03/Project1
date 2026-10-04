import pandas as pd

def scenario(pnl, revenue_growth=0, cogs_change=0, personnel_growth=0, opex_growth=0):
    x=pnl.groupby('category')[['actual']].sum().reset_index()
    v=dict(zip(x.category,x.actual))
    revenue=v.get('Revenue',0)*(1+revenue_growth)
    cogs=v.get('COGS',0)*(1+cogs_change)
    personnel=v.get('Personnel',0)*(1+personnel_growth)
    opex=v.get('Opex',0)*(1+opex_growth)
    dep=v.get('Depreciation',0)
    gp=revenue+cogs
    op=gp+personnel+opex+dep
    margin=op/revenue if revenue else 0
    return {'Revenue':revenue,'COGS':cogs,'Gross Profit':gp,'Personnel':personnel,'Opex':opex,'Depreciation':dep,'Operating Profit':op,'Operating Margin':margin}
