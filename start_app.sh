#!/bin/bash
# Start backend
cd backend
python main.py &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Wait
wait
