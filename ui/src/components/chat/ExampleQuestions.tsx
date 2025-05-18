import React from 'react';

interface ExampleQuestionsProps {
  onSelectQuestion: (question: string) => void;
  className?: string;
}

const ExampleQuestions: React.FC<ExampleQuestionsProps> = ({
  onSelectQuestion,
  className = ''
}) => {
  const questions = [
    "What are the main components of this codebase?",
    "How does the authentication system work?",
    "Explain the data flow in the application",
    "What design patterns are used in this project?",
    "Show me the implementation of the main service class"
  ];

  const handleQuestionClick = (question: string) => {
    console.log("Selected example question:", question);
    
    // Call the onSelectQuestion prop function with the selected question
    if (onSelectQuestion) {
      try {
        onSelectQuestion(question);
      } catch (error) {
        console.error("Error handling question selection:", error);
      }
    } else {
      console.error("onSelectQuestion function is not defined");
    }
  };

  return (
    <div className={`bg-blue-900/10 border border-blue-800/20 rounded-lg p-6 ${className}`}>
      <h3 className="text-xl font-bold text-blue-400 mb-4">
        Try asking questions like:
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {questions.map((question, index) => (
          <button
            key={index}
            onClick={() => handleQuestionClick(question)}
            className="
              bg-blue-900/20 hover:bg-blue-900/30
              border border-blue-800/30
              text-white text-left
              rounded-lg p-3
              transition-colors
            "
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
};

export default ExampleQuestions;
