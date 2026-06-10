from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel


class AccountReport(BaseModel):
    accounts: list[AccountData]

    @property
    def amount(self) -> int:
        """Sums amounts across all accounts

        Returns:
            int: Total amount across all accounts
        """
        return sum(acc.amount for acc in self.accounts)

    @property
    def transactions(self) -> list[list[str, int]]:
        """Flattened, enriched, and date-sorted transactions

        Returns:
            list[list[str, int]]: All transactions list across all accounts
        """
        flat_list = []
        for acc in self.accounts:
            for trans in acc.transactions:
                flat_list.append([acc.identifier] + trans.to_list())

        return sorted(
            flat_list, key=lambda x: datetime.strptime(x[1], "%d/%m/%Y"), reverse=True
        )


class AccountData(BaseModel):
    identifier: str
    amount: int
    transactions: list[Transaction]


class Transaction(BaseModel):
    date: str
    amount: int
    description: str
    location: str

    def to_list(self) -> list[str, int]:
        """Transforms transaction data into a list

        Returns:
            list[str, int]: Transaction data as a list
        """
        return list(self.model_dump().values())


class BankSheetConfig(BaseModel):
    worksheet: str
    amount_cell: str
    transactions_cell: str
    update_dateime_cell: str
