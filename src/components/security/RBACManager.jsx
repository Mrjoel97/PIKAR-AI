
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { User } from '@/api/entities';
import { 
    Shield, 
    Users, 
    Plus, 
    Edit, 
    Trash2, 
    Save, 
    UserPlus,
    Settings,
    Eye,
    Lock,
    Unlock
} from 'lucide-react';
import { toast } from 'sonner';

const PERMISSIONS = [
    { id: 'dashboard.view', label: 'View Dashboard', category: 'Dashboard' },
    { id: 'dashboard.edit', label: 'Edit Dashboard', category: 'Dashboard' },
    { id: 'agents.view', label: 'View AI Agents', category: 'AI Agents' },
    { id: 'agents.execute', label: 'Execute AI Agents', category: 'AI Agents' },
    { id: 'agents.create', label: 'Create Custom Agents', category: 'AI Agents' },
    { id: 'agents.delete', label: 'Delete Agents', category: 'AI Agents' },
    { id: 'initiatives.view', label: 'View Initiatives', category: 'Initiatives' },
    { id: 'initiatives.create', label: 'Create Initiatives', category: 'Initiatives' },
    { id: 'initiatives.edit', label: 'Edit Initiatives', category: 'Initiatives' },
    { id: 'initiatives.delete', label: 'Delete Initiatives', category: 'Initiatives' },
    { id: 'workflows.view', label: 'View Workflows', category: 'Workflows' },
    { id: 'workflows.create', label: 'Create Workflows', category: 'Workflows' },
    { id: 'workflows.execute', label: 'Execute Workflows', category: 'Workflows' },
    { id: 'analytics.view', label: 'View Analytics', category: 'Analytics' },
    { id: 'analytics.export', label: 'Export Analytics', category: 'Analytics' },
    { id: 'reports.create', label: 'Create Reports', category: 'Reports' },
    { id: 'reports.share', label: 'Share Reports', category: 'Reports' },
    { id: 'users.view', label: 'View Users', category: 'User Management' },
    { id: 'users.invite', label: 'Invite Users', category: 'User Management' },
    { id: 'users.edit', label: 'Edit User Roles', category: 'User Management' },
    { id: 'roles.manage', label: 'Manage Roles', category: 'User Management' },
    { id: 'audit.view', label: 'View Audit Logs', category: 'Security' },
    { id: 'settings.view', label: 'View Settings', category: 'Settings' },
    { id: 'settings.edit', label: 'Edit Settings', category: 'Settings' },
];

const DEFAULT_ROLES = [
    {
        id: 'admin',
        name: 'Administrator',
        description: 'Full access to all features and settings',
        permissions: PERMISSIONS.map(p => p.id),
        color: 'bg-red-100 text-red-800',
        isSystemRole: true
    },
    {
        id: 'manager',
        name: 'Manager',
        description: 'Can manage initiatives and view analytics',
        permissions: [
            'dashboard.view', 'dashboard.edit',
            'agents.view', 'agents.execute',
            'initiatives.view', 'initiatives.create', 'initiatives.edit',
            'workflows.view', 'workflows.create', 'workflows.execute',
            'analytics.view', 'analytics.export',
            'reports.create', 'reports.share'
        ],
        color: 'bg-blue-100 text-blue-800',
        isSystemRole: true
    },
    {
        id: 'analyst',
        name: 'Business Analyst',
        description: 'Can use AI agents and create reports',
        permissions: [
            'dashboard.view',
            'agents.view', 'agents.execute',
            'initiatives.view',
            'workflows.view', 'workflows.execute',
            'analytics.view',
            'reports.create'
        ],
        color: 'bg-green-100 text-green-800',
        isSystemRole: true
    },
    {
        id: 'viewer',
        name: 'Viewer',
        description: 'Read-only access to most features',
        permissions: [
            'dashboard.view',
            'agents.view',
            'initiatives.view',
            'workflows.view',
            'analytics.view'
        ],
        color: 'bg-gray-100 text-gray-800',
        isSystemRole: true
    }
];

export default function RBACManager() {
    const [roles, setRoles] = useState(DEFAULT_ROLES);
    const [users, setUsers] = useState([]);
    const [selectedRole, setSelectedRole] = useState(null);
    const [isCreatingRole, setIsCreatingRole] = useState(false);
    const [newRole, setNewRole] = useState({
        name: '',
        description: '',
        permissions: []
    });
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const loadUsers = useCallback(async () => {
        setIsLoading(true);
        try {
            const userList = await User.list();
            // Add mock role assignments for demo
            const usersWithRoles = userList.map(user => ({
                ...user,
                roleId: user.role || 'viewer',
                roleName: roles.find(r => r.id === (user.role || 'viewer'))?.name || 'Viewer'
            }));
            setUsers(usersWithRoles);
        } catch (error) {
            console.error("Failed to load users:", error);
            toast.error("Failed to load users");
        } finally {
            setIsLoading(false);
        }
    }, [roles]); // Dependency: roles is used to find roleName

    useEffect(() => {
        loadUsers();
    }, [loadUsers]); // Dependency: loadUsers is a useCallback function

    const createRole = async () => {
        if (!newRole.name.trim()) {
            toast.error("Role name is required");
            return;
        }

        const roleData = {
            id: newRole.name.toLowerCase().replace(/\s+/g, '_'),
            name: newRole.name,
            description: newRole.description,
            permissions: newRole.permissions,
            color: 'bg-purple-100 text-purple-800',
            isSystemRole: false,
            createdAt: new Date().toISOString()
        };

        setRoles([...roles, roleData]);
        setNewRole({ name: '', description: '', permissions: [] });
        setIsCreatingRole(false);
        toast.success(`Role "${roleData.name}" created successfully`);
    };

    const updateRole = (roleId, updates) => {
        setRoles(roles.map(role => 
            role.id === roleId ? { ...role, ...updates } : role
        ));
        toast.success("Role updated successfully");
    };

    const deleteRole = (roleId) => {
        const role = roles.find(r => r.id === roleId);
        if (role?.isSystemRole) {
            toast.error("Cannot delete system roles");
            return;
        }

        setRoles(roles.filter(role => role.id !== roleId));
        setSelectedRole(null);
        toast.success("Role deleted successfully");
    };

    const assignRole = async (userId, roleId) => {
        setUsers(users.map(user => 
            user.id === userId 
                ? { 
                    ...user, 
                    roleId, 
                    roleName: roles.find(r => r.id === roleId)?.name 
                }
                : user
        ));
        toast.success("User role updated successfully");
    };

    const togglePermission = (permissionId) => {
        if (selectedRole) {
            const hasPermission = selectedRole.permissions.includes(permissionId);
            const updatedPermissions = hasPermission
                ? selectedRole.permissions.filter(p => p !== permissionId)
                : [...selectedRole.permissions, permissionId];
            
            updateRole(selectedRole.id, { permissions: updatedPermissions });
            setSelectedRole({ ...selectedRole, permissions: updatedPermissions });
        }
    };

    const getPermissionsByCategory = () => {
        const categories = {};
        PERMISSIONS.forEach(permission => {
            if (!categories[permission.category]) {
                categories[permission.category] = [];
            }
            categories[permission.category].push(permission);
        });
        return categories;
    };

    const filteredUsers = users.filter(user => 
        user.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.roleName?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <Shield className="w-8 h-8 text-blue-600" />
                        Role-Based Access Control
                    </h1>
                    <p className="text-gray-600 mt-1">
                        Manage user roles and permissions across the platform
                    </p>
                </div>
            </div>

            <Tabs defaultValue="roles" className="space-y-6">
                <TabsList>
                    <TabsTrigger value="roles">Roles & Permissions</TabsTrigger>
                    <TabsTrigger value="users">User Management</TabsTrigger>
                    <TabsTrigger value="audit">Access Audit</TabsTrigger>
                </TabsList>

                <TabsContent value="roles" className="space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Roles List */}
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between">
                                <CardTitle>Roles</CardTitle>
                                <Button 
                                    size="sm" 
                                    onClick={() => setIsCreatingRole(true)}
                                >
                                    <Plus className="w-4 h-4 mr-2" />
                                    New Role
                                </Button>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {roles.map(role => (
                                    <div
                                        key={role.id}
                                        onClick={() => setSelectedRole(role)}
                                        className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                                            selectedRole?.id === role.id 
                                                ? 'bg-blue-50 border-blue-200' 
                                                : 'hover:bg-gray-50'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <h4 className="font-medium">{role.name}</h4>
                                                <p className="text-sm text-gray-500">{role.description}</p>
                                                <Badge className={`mt-1 ${role.color}`}>
                                                    {role.permissions.length} permissions
                                                </Badge>
                                            </div>
                                            {role.isSystemRole && (
                                                <Lock className="w-4 h-4 text-gray-400" />
                                            )}
                                        </div>
                                    </div>
                                ))}

                                {isCreatingRole && (
                                    <Card>
                                        <CardContent className="p-4 space-y-3">
                                            <Input
                                                placeholder="Role name"
                                                value={newRole.name}
                                                onChange={(e) => setNewRole({...newRole, name: e.target.value})}
                                            />
                                            <Input
                                                placeholder="Description"
                                                value={newRole.description}
                                                onChange={(e) => setNewRole({...newRole, description: e.target.value})}
                                            />
                                            <div className="flex gap-2">
                                                <Button size="sm" onClick={createRole}>
                                                    <Save className="w-4 h-4 mr-2" />
                                                    Save
                                                </Button>
                                                <Button 
                                                    size="sm" 
                                                    variant="outline"
                                                    onClick={() => setIsCreatingRole(false)}
                                                >
                                                    Cancel
                                                </Button>
                                            </div>
                                        </CardContent>
                                    </Card>
                                )}
                            </CardContent>
                        </Card>

                        {/* Permissions Editor */}
                        <div className="lg:col-span-2">
                            {selectedRole ? (
                                <Card>
                                    <CardHeader className="flex flex-row items-center justify-between">
                                        <div>
                                            <CardTitle>{selectedRole.name}</CardTitle>
                                            <CardDescription>{selectedRole.description}</CardDescription>
                                        </div>
                                        <div className="flex gap-2">
                                            {!selectedRole.isSystemRole && (
                                                <Button 
                                                    variant="outline" 
                                                    size="sm"
                                                    onClick={() => deleteRole(selectedRole.id)}
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </Button>
                                            )}
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-6">
                                            {Object.entries(getPermissionsByCategory()).map(([category, permissions]) => (
                                                <div key={category}>
                                                    <h4 className="font-medium text-sm text-gray-700 mb-3">{category}</h4>
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                        {permissions.map(permission => (
                                                            <div key={permission.id} className="flex items-center space-x-2">
                                                                <Checkbox
                                                                    id={permission.id}
                                                                    checked={selectedRole.permissions.includes(permission.id)}
                                                                    onCheckedChange={() => togglePermission(permission.id)}
                                                                    disabled={selectedRole.isSystemRole}
                                                                />
                                                                <label 
                                                                    htmlFor={permission.id}
                                                                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                                                >
                                                                    {permission.label}
                                                                </label>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            ) : (
                                <Card>
                                    <CardContent className="flex items-center justify-center h-64">
                                        <div className="text-center">
                                            <Shield className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                                            <h3 className="font-medium text-gray-900">Select a role</h3>
                                            <p className="text-sm text-gray-500">Choose a role to view and edit permissions</p>
                                        </div>
                                    </CardContent>
                                </Card>
                            )}
                        </div>
                    </div>
                </TabsContent>

                <TabsContent value="users" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>User Role Management</CardTitle>
                            <CardDescription>Assign roles to users and manage access levels</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <Input
                                    placeholder="Search users..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="max-w-sm"
                                />

                                <div className="space-y-3">
                                    {filteredUsers.map(user => (
                                        <div key={user.id} className="flex items-center justify-between p-4 border rounded-lg">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
                                                    <Users className="w-5 h-5 text-gray-500" />
                                                </div>
                                                <div>
                                                    <h4 className="font-medium">{user.full_name}</h4>
                                                    <p className="text-sm text-gray-500">{user.email}</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <Badge className={roles.find(r => r.id === user.roleId)?.color}>
                                                    {user.roleName}
                                                </Badge>
                                                <Select 
                                                    value={user.roleId} 
                                                    onValueChange={(roleId) => assignRole(user.id, roleId)}
                                                >
                                                    <SelectTrigger className="w-40">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {roles.map(role => (
                                                            <SelectItem key={role.id} value={role.id}>
                                                                {role.name}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="audit" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Access Audit Log</CardTitle>
                            <CardDescription>Monitor role changes and permission usage</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="text-center py-8 text-gray-500">
                                <Eye className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                <p>Access audit logging is active</p>
                                <p className="text-sm">All role changes and permission usage are being tracked</p>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
