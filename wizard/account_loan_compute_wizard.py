from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.addons.account_loans.lib.pyloan import Payment
from odoo.exceptions import ValidationError


class AccountLoanComputeWizard(models.TransientModel):
    _inherit = "account.loan.compute.wizard"

    compounding_method = fields.Selection(
        selection_add=[("emi", "EMI")], ondelete={"emi": "set default"}
    )

    def _get_loan_payment_schedule(self):
        self.ensure_one()
        if self.compounding_method != "emi":
            return super()._get_loan_payment_schedule()
        return self._tha_get_emi_payment_schedule()

    def _tha_get_emi_payment_schedule(self):
        self.ensure_one()
        if self.loan_amount <= 0 or self.loan_term <= 0:
            return []
        if not 0 <= self.interest_rate <= 100:
            raise ValidationError(_("Interest Rate must be between 0 and 100"))

        duration = self.loan_term * 12
        monthly_rate = self.interest_rate / 1200.0
        if monthly_rate:
            factor = (1 + monthly_rate) ** duration
            emi_amount = self.loan_amount * monthly_rate * factor / (factor - 1)
        else:
            emi_amount = self.loan_amount / duration

        currency = self.currency_id
        balance = currency.round(self.loan_amount)
        first_month_end = self.start_date + relativedelta(day=31)
        if self.start_date == first_month_end:
            first_month_end += relativedelta(months=1, day=31)
        schedule = []
        for index in range(duration):
            if self.payment_end_of_month == "end_of_month":
                payment_date = first_month_end + relativedelta(months=index, day=31)
            else:
                payment_date = self.first_payment_date + relativedelta(months=index)

            interest = currency.round(balance * monthly_rate)
            principal = min(currency.round(emi_amount - interest), balance)
            if index == duration - 1:
                principal = balance
            balance = currency.round(balance - principal)
            schedule.append(Payment(
                date=payment_date,
                payment_amount=principal + interest,
                interest_amount=interest,
                principal_amount=principal,
                special_principal_amount=0.0,
                total_principal_amount=principal,
                loan_balance_amount=balance,
            ))
        return schedule
