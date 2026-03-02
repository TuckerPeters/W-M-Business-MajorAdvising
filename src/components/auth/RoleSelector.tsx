"use client";
import { useRouter } from "next/navigation";

export default function RoleSelector() {
  const router = useRouter();

  const handleStudent = () => {
    router.push("/student");
  };

  const handleAdvisor = () => {
    router.push("/advisor");
  };

  return (
    <div className="flex flex-col gap-4">
      <button 
        onClick={handleStudent}
        className="bg-blue-600 text-white py-2 rounded"
      >
       I am a Student
      </button>
      
      <button
        onClick={handleAdvisor}
        className="bg-purple-600 text-white py-2 rounded"
      >
        I am an Advisor
      </button>
    </div>
  );
}
