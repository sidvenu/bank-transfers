# Bank Transfers

A simple Flask app that implements an intra-bank accounts transfer.

## Environment Setup

You need to have [Pipenv](https://pypi.org/project/pipenv/) to run this project.

## Instructions to run

1. Run `pipenv install`.
2. Run `pipenv install --dev` for dev dependencies - you do not require this if you only need to run the production
   server.
3. Run `flask run`. You will now notice the server running on port 5000 in your computer.

This project uses SQLite as its database. You need to have a `main.db` in your project root that has the required tables
and initial data.

If you do not have this `main.db`, you can call the API `POST http://localhost:5000/init-db`
to create all tables and write the initial data to the database.

## Postman Collection

You can access the Postman Collection for this
project [here](https://www.getpostman.com/collections/2dc27c97f19a9276b93e).

## Considerations

1. All amounts are stored in paise - therefore the datatype is an integer.
2. A user can accept multiple transfers at the same time.
3. A user can make multiple transfers concurrently - transfers can fail if the user does not have enough balance in
   their account.
4. Since the transfer method will have a Database Transaction running throughout and is commited at the end, if say the
   database connection severs in the middle, the transaction will be rolled back and Flask will return a 500 status to
   the client.

## DB Schema Changes

1. `transactions` table has `initiate_ts` and `complete_ts` instead of `create_datetime`. I understand that
   by `datetime` it means a datetime string of a particular format. A Unix Timestamp is much easier to work with
   especially across multiple frameworks and environments (browser/server). Also, we need both timestamps of when the
   transaction was initiated and when it was completed. The word 'create' is confusing - is it when the transaction was
   created or when the transaction row was created? It is better to have words that are not ambiguous - therefore '
   initiate' and 'complete' fit the bill.

## API Response Changes

1. I am not returning the recipient's balance in the response. It seems to me that this API will probably be used by a
   Net Banking frontend to carry out the transfer, and if it going to be directly queried by the frontend, any person
   can view anyone else's balance by just transferring 1 rupee to their account.
2. I am returning both initiate and completed datetimes, instead of create datetime.
