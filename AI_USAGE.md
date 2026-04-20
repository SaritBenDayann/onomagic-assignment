# AI Usage Documentation

As a student, I approached this assignment by using Gemini as a "pair programmer." My goal was to be the architect driving the design and logic, while using the AI to help me type out the boilerplate code and Python syntax faster. 

### Step 1: Planning the Architecture (My Decision)
Before writing any code, I mapped out how the app should be structured. I wanted to avoid a messy `app.py` file that does everything. I decided to use a **Layered Architecture** (Controller -> Service -> Repository) to keep things clean. 
I also chose to use an In-Memory dictionary for the database to keep the setup simple for the reviewer, but I wrapped it in an Interface so it could theoretically be swapped out for a real DB later.

### Step 2: Generating the Base Classes (AI Assistance)
Once I had my blueprint, I used prompts to ask the AI to generate the foundational code. For example, I asked it to create Python `dataclasses` for the `Allocation` entity and set up the basic Flask routing. The AI was very helpful in generating this repetitive boilerplate quickly.

### Step 3: Implementing Business Logic & Testability (My Design + AI Execution)
The core of the assignment was the rules (24h cooldown, 5-minute cancel window). I asked the AI to write this logic inside the `ChannelAllocationService`. 
**My specific correction:** I realized that testing time-based logic (like waiting 5 minutes) is tricky. I instructed the AI to use **Dependency Injection** for the time mechanism (passing a `get_time_func` to the service). This was my design choice so I could mock the clock in my automated tests later without using `time.sleep()`.


### Step 4: Frontend Development (My Logic + AI Styling)
For the UI, I prioritized functional clarity over visual polish. I designed the component tree (`AllocationForm`, `ActiveChannelsTable`) and instructed the AI to generate the React boilerplate and basic CSS.
* **My Correction:** To maintain clean components, I manually extracted all `fetch` logic into a dedicated `apiClient.js` service layer. I also enforced UI state locks to prevent users from firing overlapping requests.

### Step 5: Code Review and Validation (My Part)
I reviewed the generated code line by line to ensure adherence to the requirements and my logic:
* I manually adjusted HTTP status codes to reflect precise backend semantics (`409 Conflict` for duplicates, `404 Not Found` for pool exhaustion).
* I wrote comprehensive edge-case tests (DST jumps, midnight crossovers, exact boundary limits) to validate the business rules beyond the basic AI generation.

**Summary:** The AI handled the typing and syntax, but the architectural decisions, the testability design, and the final code validation were completely mine.