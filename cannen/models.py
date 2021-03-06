# This file is part of Cannen, a collaborative music player.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from urllib import unquote

import backend

UPLOAD_TO = "uploaded/"

# model for files uploaded
class SongFile(models.Model):
    owner = models.ForeignKey(User)
    file = models.FileField(upload_to=UPLOAD_TO, storage=backend.get().get_storage())
    
    def garbage_collect(self):
        if self.globalsong_set.count() > 0 or self.usersong_set.count() > 0:
            return
        # we're no longer needed, so delete!
        self.delete()

@receiver(post_save, sender=SongFile)
def register_uploaded(sender, **kwargs):
    if kwargs['created']:
        instance = kwargs['instance']
        backend.get().register_uploaded(unquote(instance.file.url))

@receiver(pre_delete, sender=SongFile)
def unregister_uploaded(sender, **kwargs):
    instance = kwargs['instance']
    url = instance.file.url
    instance.file.delete(save=False)
    backend.get().unregister_uploaded(unquote(url))

# for user-local queues
class UserSong(models.Model):
    owner = models.ForeignKey(User)
    url = models.CharField(max_length=200)
    file = models.ForeignKey(SongFile, null=True, blank=True)
    
    class Meta:
        ordering = ['id']
    
    def __unicode__(self):
        return self.url.rsplit('/')[-1]

@receiver(post_delete, sender=UserSong)
def user_song_delete(sender, **kwargs):
    instance = kwargs['instance']
    if instance.file:
        instance.file.garbage_collect()

def add_song_and_file(user, file):
    newfile = SongFile(owner=user, file=file)
    newfile.save()
    newsong = UserSong(owner=newfile.owner, url=unquote(newfile.file.url), file=newfile)
    newsong.save()
    return (newsong, newfile)

# for the global queue
class GlobalSong(models.Model):
    submitter = models.ForeignKey(User)
    url = models.CharField(max_length=200)
    file = models.ForeignKey(SongFile, null=True, blank=True)
    is_playing = models.BooleanField()
    
    class Meta:
        ordering = ['id']
    
    def __unicode__(self):
        return self.url.rsplit('/')[-1]
    
    @classmethod
    def from_user_song(cls, user):
        return cls(submitter=user.owner, url=user.url, file=user.file, is_playing=False)

@receiver(post_delete, sender=GlobalSong)
def global_song_delete(sender, **kwargs):
    instance = kwargs['instance']
    if instance.file:
        instance.file.garbage_collect()
