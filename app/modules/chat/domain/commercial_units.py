from decimal import Decimal

# The business bought 50 kg bags historically, then switched exclusively to
# 25 kg bags when the former presentation disappeared. Historical records keep
# their actual presentation; current commercial requests use this conversion.
CURRENT_CEMENT_BAG_KG = Decimal("25")
