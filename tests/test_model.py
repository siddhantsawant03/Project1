from src.model import demo

def test_demo_model():
    a,b,f=demo(); assert len(a)>0; assert set(a.category.unique())=={'Revenue','COGS','Personnel','Opex','Depreciation'}
