import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Clock, TrendingUp, FileText, Trash2 } from 'lucide-react';

const RecentTransactions = () => {
  const navigate = useNavigate();

  const handleViewDetails = (id: string) => {
    navigate(`/transactions/${id}`);
  };

  const handleDelete = (id: string) => {
    // Implement delete logic
    console.log(`Deleting transaction ${id}`);
  };

  return (
    <div className="space-y-4">
      {/* Example transaction row */}
      <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
            <Clock className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h3 className="font-medium">Weekly Sales Report</h3>
            <p className="text-sm text-gray-500">Generated 2 hours ago</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={() => handleViewDetails('txn-001')}>
            View Details
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleDelete('txn-001')}>
            Delete
          </Button>
        </div>
      </div>

      {/* Additional transaction rows would go here */}
    </div>
  );
};

export default RecentTransactions;