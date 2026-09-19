"""
BUCKET SCALES - the numbers that decide green, orange, blue or red.

WHAT IT DOES
    Holds one Scale per category and answers one question: given a return of
    9% per year, which of the four groups does it belong to?

WHY EACH CATEGORY HAS ITS OWN SCALE
    A debt fund almost never returns more than 10% a year. Judged on the equity
    scale, every debt fund would look bad - when it is actually working
    normally. So equity green starts at 10%, debt green starts at 8%.

        9% per year  ->  equity: moderate     debt: strong

    This is also why rule M-6 says the scale must always be visible on screen.
    Without it, a user compares a debt meter to an equity meter and draws the
    wrong conclusion.

SOURCE
    PRD section 6.4. These numbers closed open item 22.6 in the original PRD.

USED BY
    meter/engine.py (to bucket each window), step0.py (to print the labels)
"""
from dataclasses import dataclass
from typing import Final

from constants import Bucket, Category


@dataclass(frozen=True)
class Scale:
    category: Category
    strong: float       # at or above this -> STRONG
    moderate: float     # at or above this -> MODERATE
    flat: float         # at or above this -> FLAT, below -> LOSS

    def bucket(self, annualised: float) -> Bucket:
        if annualised >= self.strong:
            return Bucket.STRONG
        if annualised >= self.moderate:
            return Bucket.MODERATE
        if annualised >= self.flat:
            return Bucket.FLAT
        return Bucket.LOSS

    def labels(self) -> dict[Bucket, str]:
        """Rule M-6: the scale in use is always visible on the meter."""
        return {
            Bucket.STRONG: f"Above {self.strong:.0%} per year",
            Bucket.MODERATE: f"{self.moderate:.0%} to {self.strong:.0%} per year",
            Bucket.FLAT: f"{self.flat:.0%} to {self.moderate:.0%} per year",
            Bucket.LOSS: "Below 0%",
        }


SCALES: Final[dict[Category, Scale]] = {
    Category.EQUITY: Scale(Category.EQUITY, 0.10, 0.04, 0.0),
    Category.HYBRID: Scale(Category.HYBRID, 0.10, 0.05, 0.0),
    Category.DEBT:   Scale(Category.DEBT,   0.08, 0.06, 0.0),
    Category.STOCK:  Scale(Category.STOCK,  0.15, 0.07, 0.0),
}
