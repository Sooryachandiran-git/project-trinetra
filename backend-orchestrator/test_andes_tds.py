import andes
s = andes.System()
s.config.save = False
s.TDS.config.tf = 5.0
s.TDS.config.store_z = 1
s.Bus.add(idx='b1', Vn=110)
s.Bus.add(idx='b2', Vn=20)
s.Bus.add(idx='b3', Vn=20)

# Slack MUST have an idx. Let's use 'gen_slack'
s.Slack.add(idx='gen_slack', bus='b1', v0=1.0, a0=0)

# We must add a SynGen, e.g. GENCLS, pointing to gen_slack
s.GENCLS.add(idx='g1', bus='b1', gen='gen_slack', Sn=100, Vn=110, H=5.0, D=0.0, Xd1=0.2, ra=0.01)

s.PQ.add(idx='load', bus='b3', p0=1.5, q0=0.2)
s.Line.add(idx='l1', bus1='b1', bus2='b2', r=0.01, x=0.1, Vn1=110, Vn2=20, trans=1.0)
s.Line.add(idx='l2', bus1='b2', bus2='b3', r=0.02, x=0.2, Vn1=20, Vn2=20)
s.Toggler.add(idx='trip', model='Line', dev='l1', t=2.0)

try:
    s.setup()
    s.PFlow.run()
    s.TDS.run()
    print("TDS SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("TDS Error:", e)
