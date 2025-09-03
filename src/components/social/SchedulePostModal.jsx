import React, { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { SocialPost } from '@/api/entities'
import { toast } from 'sonner'

const timezones = [
  'UTC','America/Los_Angeles','America/New_York','Europe/London','Europe/Berlin','Asia/Tokyo','Asia/Singapore'
]

export default function SchedulePostModal({ open, onOpenChange, post, onSaved }) {
  const [publishAt, setPublishAt] = useState('')
  const [timezone, setTimezone] = useState('UTC')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (post?.scheduled_time) {
      try {
        const dt = new Date(post.scheduled_time)
        setPublishAt(dt.toISOString().slice(0,16))
      } catch {}
    } else {
      setPublishAt('')
    }
    setTimezone(post?.timezone || 'UTC')
  }, [post])

  const handleSave = async () => {
    if (!post) return
    if (!publishAt) {
      toast.error('Please select a date/time')
      return
    }
    setSaving(true)
    try {
      await SocialPost.update(post.id, {
        scheduled_time: new Date(publishAt).toISOString(),
        timezone,
        status: 'scheduled'
      })
      toast.success('Post scheduled')
      onSaved?.()
      onOpenChange(false)
    } catch (e) {
      console.error(e)
      toast.error('Failed to schedule post')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Schedule Post</DialogTitle>
          <DialogDescription>Choose when to publish this post.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Publish at</Label>
            <Input type="datetime-local" value={publishAt} onChange={e => setPublishAt(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Timezone</Label>
            <Select value={timezone} onValueChange={setTimezone}>
              <SelectTrigger>
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent>
                {timezones.map(tz => (<SelectItem key={tz} value={tz}>{tz}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save schedule'}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

