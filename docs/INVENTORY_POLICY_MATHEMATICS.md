# Inventory policy mathematics and units

These are discrete periodic end-of-day reviews, not continuous-review equations.
Let mu be trailing56-day observed training mean, L intervening demand days, review
interval R, P=L+R, buffer B=b*mu, and inventory position IP=closing stock+pipeline.
Lost sales are not backlogged. All quantities/orders are nonnegative; replenishment
orders round upwards to integer units. There is no capacity or minimum-order constraint.

Fixed reorder comparator: s=mu*P+B, Q=ceil(mu*R). At an eligible review, order Q
if IP<=s and Q>0, otherwise zero. This is a fixed (s,Q) periodic comparator; Q is
not repeatedly issued until a target is reached and s is not daily recalibrated.

Forecast policies share order-up-to mathematics: S=sum(p[d],d=t+1..t+P)+B,
order=ceil(max(0,S-IP)). Input p is existing MA28, seasonal naive, or the frozen
selected ML validation forecast. Both timing and B are common across policies.
An unavailable forecast date is an error; no true demand substitutes for it.

Conservation each day: A=opening+receipts; fulfilled=min(A,D); unmet=D-fulfilled;
closing=A-fulfilled; pipeline_after=pipeline_before-receipts+new_order.
Orders placed on t enter receipts on t+L+1. Initial scheduled receipts, if supplied
in synthetic fixtures, are already-known pipeline; empirical episodes start empty.

Costs use normalised hypothetical cost units (NCU): h*closing per day, p*unmet,
k for each positive order, v*ordered_units at placement (including unreceived units),
and terminal e*(last_closing+last_pipeline). Base h=1,p=10,k=1,v=0,e=0. No salvage
credit or claim of real currency values. Terminal-charge sensitivity e=1 penalises
remaining exposure. Initial acquisition cost is excluded and starting stock is common.
This is finite-episode cost accounting, not lifetime economic optimisation.

Pooled fill rate=sum(fulfilled)/sum(demand), undefined at zero demand; macro fill
averages defined series only. Stockout-day rate=days(unmet>0)/28 and is not cycle
service level. Average on-hand is mean daily closing stock; average IP is mean
end-of-day post-order position. Average order size is undefined for zero orders.
Window turnover=fulfilled/mean_closing is undefined for zero denominator. Do not
replace undefined values by zero. Include initial/received/fulfilled/terminal stock
and placed/received/terminal pipeline conservation in every result.
