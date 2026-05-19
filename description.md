Team Project
A major component of this course is a software development project in team efforts. Your team will propose, design, develop, and maintain a practical and production-level software product.
Below is a list of projects you may select from.
1. Campus Social Marketplace
Every university has a market of lost-and-found items, second-hand textbooks, and unshared skills that currently live in fragmented WeChat groups or expired forum posts. Information gets buried, and trust is hard to verify. Your goal is to build a Web application designed specifically for the micro-economy of SUSTech campus life.
Potential Features:
Trust-Based Trading: A listing system for goods/services integrated with student ID verification and a "reputation score" based on previous successful exchanges.
Smart Matching: An automated notification system that alerts users when an item on their "Wishlist" (e.g., a specific Calculus textbook) is posted.
Skill Exchange: A feature allowing students to trade "skills" (e.g., 1 hour of Python tutoring for 1 hour of guitar lessons).
Campus Trade Map: An interactive map showing where "Found Items" are located or where the best places are to meet for a trade.
Chatroom: A real-time chat interface for buyers and sellers with price negotiation and appointment scheduling.
2. SUSTech Adventure Game
It is Finals Week at SUSTech. You just woke up in your dorm, and you realize your Software Engineering exam starts in 30 minutes at the 3rd Teaching Building, but you've realized you left your student ID card and cheat sheet somewhere on the other side of campus!
Your goal is to build an adventure game where the player must navigate the SUSTech campus to collect their "Exam Essentials" and reach the exam hall before the doors lock.
Required Features:
Campus Map: The game must include key locations on SUSTech campus like Lynn Library.
Potential Features:
NPC Interaction: For example, the player may talk to "Security Guards" to get clues about the lost student card.
Campus Transport: Include the Campus Shuttle Bus as a fast-travel mechanic between the dorm and the destination.
Mini-Games: Specific locations trigger mini-games (e.g., a quiz at the Library to earn extra time).
Inventory System: Collect items like "Library Vouchers" or "Lychees" to gain extra time or unlock new areas.
3. Student Productivity Agent
Being a student at SUSTech is a high-speed balancing act. You have deadlines on Blackboard, events on the University Calendar, and your own Personal TODOs scattered across different apps. It's easy to feel overwhelmed when these sources don't talk to each other.
Your goal is to build an Autonomous AI Agent designed to be your digital partner. Unlike a traditional app where you do all the clicking, the agent can reason about your goals and act on your behalf to clean up your schedule, organize your files, and hunt down campus information.
Mandatory Architecture
Your system must follow the Agentic Loop architecture:
Perception: Receive a natural language request (e.g., "I'm stressed about finals, help me plan").
Reasoning & Planning: The LLM decides which tools to use and in what order.
Tool Use: The system calls real tools (e.g., python functions) to interact with the file system, APIs, or data.
Observation: The Agent reads the tool's output, checks for errors, and decides if it needs to try a different approach.
Mandatory UI
A Command Line Interface (CLI) is not enough. Your project must include a GUI that serves 3 purposes:
Interaction: A clean way to chat and view results (e.g., rendered calendars, file lists).
Thought Trace: A dedicated area showing the Agent's internal logic: which tools it is calling and why.
Human-in-the-Loop: A confirmation mechanism where the Agent asks for permission before performing "heavy" actions like updating calendars.
Implementation Policy
If your system behaves like a traditional program with fixed rules, hardcoded logic or pre-scripted workflow, instead of letting the LLM dynamically decide what to do, then the project does not satisfy the requirements.
No Low-Code/No-Code: Use of visual "drag-and-drop" platforms like n8n or Dify is prohibited.
While you are encouraged to use frameworks like PydanticAI, you should implement most of the core logic, such as the tools (actions), error handling, memory management, and GUI integration.
Potential Agent Capabilities (Tools)
Multi-Source Scheduler: Build tools that allow the Agent to read from the Official University Calendar, your Blackboard deadlines, and your Personal TODO list. The Agent should automatically detect time conflicts and suggest an optimized plan.
Campus Encyclopedia: Build a retrieval tool for University Handbooks. The Agent should answer complex questions like "How many credits do I need to minor in Physics?" or "What is the deadline for changing my dorm?" by reading official documents.
Study Copilot: Create a tool that processes lecture PPTs or Markdown notes. The Agent should be able to generate quizzes or summaries based on these specific materials.
Automation Scripts: Create system-level tools that allow the Agent to perform tasks like "Rename all my lab files to [Name_ID_Lab1].zip" or "Monitor library seat availability and alert me when a spot opens."
4. HarmonyOS App Innovation (鸿蒙应用开发)
In this track, you will learn to build applications for the HarmonyOS (鸿蒙) ecosystem. Specifically, you will create an app that runs directly on HarmonyOS devices.
You have the freedom to choose any topic (e.g., campus life, health, productivity), provided that the app meets the basic requirements of the team project (see below). In other words, your project must be a "Non-Trivial Application." This means your topic must be complex enough to require meaningful software engineering, data management, and UI design. Simple "utility" apps (like a basic calculator) will not meet the course standards.
Technical Requirements
To ensure you are learning the official HarmonyOS development path, your team must use:
Language: ArkTS (The standard language for HarmonyOS).
UI Framework: ArkUI (Declarative UI framework).
IDE: DevEco Studio (The official IDE).
Native implementation: You are not allowed to simply take a website URL and put it inside a "Web View" or a browser-like frame. The app should be built from scratch using HarmonyOS ArkTS and ArkUI components, not just a shortcut to a website. You may use Java or other programming languages for developing the backend, yet the core features should be implemented on the frontend by ArkTS.
5. "China Software Cup" Competition
This track is designed for students who wish to align their coursework with a real-world entry into a national-level software contest: the "China Software Cup" College Student Software Design Competition (中国软件杯-大学生软件设计大赛). It offers a unique path to apply software engineering principles to complex, industry-defined problems while representing SUSTech on a national stage.
Because the competition season typically begins in the middle of the semester, this track is divided into a Preparation Phase and a Live Competition Phase.
Phase 1: Preparation (Weeks 1 – 9)
During the first two milestones, teams will focus on "Training" using problems from the past three years (2023–2025) of competition archives. Your team has the freedom to choose any historical competition problem from below.
Problem Set for the 14th Competition (2025)
Problem Set for the 13th Competition (2024)
Problem Set for the 12th Competition (2023)
For Milestones 1 and 2, you will follow the same standard requirements and grading rubrics applied to all other project tracks.
Phase 2: Live Competition (Weeks 10 – 15)
Once the 2026 competition problems are officially released (typically around Week 9), teams in this track will transition to the live event.
Topic Transition: Your team will select a newly released 2026 problem and begin following the specific requirements and technical instructions provided by the competition organizers.
Mandatory Registration: Teams must officially register for the 2026 competition and provide proof of registration to the teaching staff.
Independent grading: Milestone 3 for this track uses an independent rubric that acknowledges the high complexity and external constraints of the competition. You are graded on your engineering rigor and progress by week 16, regardless of the competition's final outcome in July.
If a team is unable to register for a live 2026 competition by Week 10, they will revert to the standard track and complete their original 2023–2025 project for Milestone 3.
Phase 3: Into the Arena (Week 15+) — Optional
The journey continues beyond the classroom. This final phase is for teams committed to seeing their project through to the national stage.
Continued Development: After the semester ends, teams are encouraged to continue refining their work.
Submission: Final submission to competition organizers usually occurs in July.
This is your chance to turn a course project into a nationally recognized innovation. Try your best to get into the final round and win an award.
While Phase 3 will not affect your course grade, the experience of competing at the highest level is an invaluable addition to any engineer's portfolio. Let's go for the Prize!
Difficulty Bonus
The bonus points varies by project:
Campus Social Marketplace: No Bonus
SUSTech Adventure Game: 3% Bonus
Student Productivity Agent: 4% Bonus
HarmonyOS App: 4% Bonus (+2%*)
The China Software Cup competition: 7% Bonus**
*+2% Store Bonus: Awarded only if the app is successfully published on the HUAWEI AppGallery.
**7% Competition Bonus: Full bonus awarded only upon official registration and proof of significant progress.
To be eligible for the difficulty bonus, your project must satisfy mandatory requirements and reach a sufficient level of maturity. A half-finished or poorly implemented project will not be eligible for bonus.
Basic Requirements
The final software product should be functional, operational, and user-friendly, providing a meaningful solution to the problem at hand.
Your project should implement at least 5 distinct and notable features. These features should be clearly distinguishable from one another and add significant value to the project, which will be outlined later in the project proposal requirement. The potential features listed in this document are only examples but not hard requirements; you can propose other features based on your project's needs and goals.
All projects must use git in GitHub Classrooms to manage the source code, documentation, and other essential project artifacts. This ensures proper collaboration, code history tracking, and project management. See lab 1 for details.
Milestones & Deliverables
The team project has 3 milestones, in week 5 (proposal), week 9 (the 1st sprint), and week 14/15 (the 2nd sprint), respectively.
At each milestone, each team is required to:
Submit a set of deliverables. Typical deliverables include working code, documentation, report, configuration files, test suites, etc.
Deliver a 10-minutes presentation during the lab session.
The three primary criteria for a successful project are: satisfying the client's needs, usability of the product, and maintainability over the life of the product. Please take these criteria in mind when developing your project.
Detailed requirements and grading scheme will be released before each milestone.