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

### Step 4: Code Review and Validation (My Part)
After the AI generated the functions, I went over them line by line to verify they met the assignment's exact requirements and my logic. 
* I manually adjusted the HTTP response codes to make sure they made sense (e.g., ensuring a duplicate active allocation returns a `409 Conflict` and an empty pool returns `404 Not Found`).
* I reviewed the dictionary iterations in the Repository to ensure they actually enforce the "active uniqueness" rule for the `(ad_id, platform)` pairs.

**Summary:** The AI handled the typing and syntax, but the architectural decisions, the testability design, and the final code validation were completely mine.