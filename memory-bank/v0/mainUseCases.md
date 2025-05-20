# Project Focus - Main Use Cases

Twincore needs to be able to retrieve context on a variety of queries - all of:
- a user's personal documents
- the shared group documents (team or project knowledgebase)
- meeting/session transcripts
- chat messages in the group chat
- chat messages beween the users to their twins
- other sources like email, slack etc (not in v0)

Common example use cases/queries we'd need to handle are:
"Did I forget someone's feedback?" "Is there anything I need to remind people about?"
  * Product feedback: Did someone (especially if they aren’t here!) mention they wanted xyz design decision, that's not represented here?
    * look at prevous meeting transcripts, email, slack messages, etc and compare to the current meeting transcript
  * Is there some context from a document that’s not represented? (Dense document comments, inconsistencies from some previous decision/point)
  * Customer Feedback: Does x design decision align with what customers are saying/actual data from the companfy?
* Example: We are building a UI, have had a previous meeting, we think we are done, and I ask the twin “did I forget someone’s feedback?” And it pulls up:
  * a message from Alice who said “we need to update the company logo to match new one”
  * a specific document detailing cost-benefit analysis of using S3 instead of existing data solution
  * Flags that 2 customers have had issues with payment system that still wasn’t addressed, this was stated in a previous transcript

A query at the start of a session could be:
- "What should the agenda for this meeting be?"
- "What are the most important action items from the last meeting to cover?"
- "What decisions have we made so far, and what do we still need to decide?"

Another common use case might be directed to the digital twins, like:
- "what would everyone think about decision XYZ?" (especially for the people who are part of the project but aren't in the current session)
- "what would Alice want in this scenario?"
- "what does everyone think about topic XYZ?"
- "what are everyone's pain points from previous sessions that we haven't spoken about yet?"

Or the user might be chatting with their digital twin in a private chat, which would need to pull from their personal documents/chats as well as the group documents/transcripts:
- "Did I forget to bring up something I mentioned before in a previous session?" (pull from current and previous transcript)
- "What are all the action items that I still need to do?" (pull from current and previous transcripts)
- "Is there something I should bring up?" (pull from personal docs/chats and current transcript)
- "What do other people think about XYZ?" (pull from other people's digital twins)

The idea is that the twin knows everything about you, as well as the public/shared knowledge base, so it can remind you when you miss something and answer questions for you, AND it can represent you to the Canvas agent when it's asking about what you think/prefer. 

Implementation thoughts:
- We could use a large-context-window LLM like Gemini 2.5 Pro. Our thought is to grab ALL the documents (transcripts etc) from previous sessions for the project, and send all of that to the LLM to answer these questions.
    - Let's assume for v0 that we don't have a huge amount of documents or messages - maybe a project only has 20 documents/transcripts/chat logs associated with it, and sessions are under 60 minutes.
    - Using Neo4j, we could grab all the documents and preferences related to a topic or project or user, and send all of those to the LLM. Or we could just grab all the documents related to a project, size permitting.
- An alternative is chunk-based RAG (Qdrant) like we currently have, but that might not be necessary if a large-content-window LLM already suffices.
- To test this we should write two separate scripts - one script sending whole documents to Gemini, and one using our current Qdrant + Neo4j ingestion with RAG semantic search for the most relevant chunks to send to Gemini. We should spin up some mock documents and transcripts (as realistic as possible, these should be 30-60-min long transcripts), as well as user<>twin and user personal documents. Then we'll feed this same sample data to a Gemini agent and compare the responses between these scripts.


What's critical now is easy, frictionless data ingestion:
- in v0, the users can manually upload a folder to ingest (assume it has the previous transcripts), as well as a folder for their personal notes
- in v1, we should have a plugin that can ingest a Google Drive folder, and auto-updates when it receives new files
- ideally, we want to be able to ingest email and slack channels too