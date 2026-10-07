import pytest
from concurrent.futures import ThreadPoolExecutor

from django.db import connections

from reservations.services import create_reservation
from reservations.models import Reservation


def _run_concurrent(fn, args_list):
    """
    Run fn(**kwargs) concurrently in threads.
    Each thread closes its own database connection.
    """
    results = []

    def worker(kwargs):
        try:
            result = fn(**kwargs)
            return (result, None)
        except Exception as e:
            return (None, e)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(args_list)) as executor:
        futures = [
            executor.submit(worker, kwargs)
            for kwargs in args_list
        ]

        for future in futures:
            results.append(future.result())

    return results


@pytest.mark.django_db(transaction=True)
class TestConcurrency:

    def test_stock_1_two_concurrent_users_only_one_wins(
        self,
        user_factory,
        product_factory,
    ):
        u1 = user_factory(username="c1")
        u2 = user_factory(username="c2")

        p = product_factory(
            name="LimitedPS5",
            stock=1,
        )

        results = _run_concurrent(
            create_reservation,
            [
                {
                    "user": u1,
                    "product_id": p.id,
                    "quantity": 1,
                },
                {
                    "user": u2,
                    "product_id": p.id,
                    "quantity": 1,
                },
            ],
        )

        successes = [
            result
            for result, error in results
            if result is not None
        ]

        failures = [
            error
            for result, error in results
            if error is not None
        ]

        assert len(successes) == 1, (
            f"Expected 1 success, got {len(successes)}. "
            f"Errors: {failures}"
        )

        p.refresh_from_db()
        assert p.stock == 0

        assert Reservation.objects.filter(
            product=p
        ).count() == 1

    def test_stock_5_ten_concurrent_users(
        self,
        user_factory,
        product_factory,
    ):
        users = [
            user_factory(username=f"u{i}")
            for i in range(10)
        ]

        p = product_factory(
            name="PS5",
            stock=5,
        )

        args_list = [
            {
                "user": user,
                "product_id": p.id,
                "quantity": 1,
            }
            for user in users
        ]

        results = _run_concurrent(
            create_reservation,
            args_list,
        )

        successes = [
            result
            for result, error in results
            if result is not None
        ]

        failures = [
            error
            for result, error in results
            if error is not None
        ]

        assert len(successes) == 5, (
            f"Expected 5 successes, got {len(successes)}. "
            f"Errors: {failures}"
        )

        p.refresh_from_db()
        assert p.stock == 0

        assert Reservation.objects.filter(
            product=p
        ).count() == 5