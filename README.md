# Channel Allocation Service

This is a backend service for managing channel identifiers (`ono1` to `ono99999`) and allocating them to ad campaigns. 

My main goal for this assignment was to focus on **core backend fundamentals**: writing clean, readable code, ensuring robust business logic, handling edge cases, and making the system fully testable without over-engineering.

## Setup and Run Instructions

### Prerequisites
* Python 3.10+ installed on your machine.

### Installation
1. Clone or extract the repository.
2. Open your terminal in the project directory.
3. Create a virtual environment:
   ```bash
   python -m venv venv
Activate the virtual environment.

Install the required dependencies:

Bash
pip install flask flask-cors pytest
Running the Server
Run the Flask application with the following command:

Bash
python app.py
The server will start on http://127.0.0.1:5000.

Testing
I wrote a comprehensive test suite to cover business rules, API routing, edge cases, and concurrency.

To run the automated tests, simply run:

Bash
pytest -v
Bonuses Completed in Tests:

Stress/Concurrency Tests: Added a test using ThreadPoolExecutor (50 threads) to ensure no double-allocations occur under heavy concurrent load.

Time Edge-Cases: Added specific tests to verify that the 24-hour cooldown and 5-minute cancel window behave correctly during DST shifts and across midnight boundaries.

Design Choices and Principles
To keep the codebase maintainable, I followed a Layered Architecture approach, separating the code into three main layers:

API / Controller Layer (app.py): handles HTTP requests, JSON parsing, and returning the correct HTTP status codes.

Business Logic / Service Layer (service.py): holds all the rules (24h cooldown, 5-min cancel window).

Testability: I used Dependency Injection to pass a get_time_func (a clock) into the service. This allowed me to mock time in my unit tests and test the 24-hour/5-minute rules instantly without using time.sleep().

Concurrency Safety: I implemented a threading.Lock within the service to wrap the read modify write transactions. This prevents where two threads might grab the same available channel simultaneously.

Data Access / Repository Layer (repository.py): * I defined an abstract Interface (ChannelRepository). The service doesn't care how data is saved, just that it fulfills the contract.

Data Structures: The current implementation (InMemoryChannelRepository) uses a dictionary. This provides O(1) time complexity for finding channels by their ID, making operations very fast.

I also used DataClasses for entities and Enums for platforms to ensure type safety and avoid magic numbers in the code.

Trade-offs and Assumptions
In-Memory Storage vs. Real Database: * Trade-off:To keep the reviewer's setup simple, I chose not to set up a real database. Data is cleared when the server restarts.

Mitigation: Because I used a Repository Interface, swapping the InMemoryRepository for a PostgresRepository in the future would require zero changes to the business logic or API layer.

Timezones: * Assumption: I assume all internal timestamps (allocated_at, available_at) are handled in UTC. This prevents bugs related to local server times or DST jumps.

What I would do next with more time
If I had more time to expand this project, I would implement the following:

Persistent Storage: Replace the in-memory repository with a real relational database.

Dockerization: Add a Dockerfile and docker-compose.yml to spin up the backend with a single command.

Frontend UI: Build the frontend to connect to this API, complete with loading states and proper user feedback.