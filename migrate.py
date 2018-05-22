#! /usr/bin/python
# -*- coding: utf-8 -*-

import gitlab
import urllib3
import os

urllib3.disable_warnings()

legacyConnection = gitlab.Gitlab.from_config('legacy', ['./gitlab.cfg'])
newerConnection = gitlab.Gitlab.from_config('newer', ['./gitlab.cfg'])
# newerConnection.enable_debug()

legacyGroups = legacyConnection.groups.list(all=True)
legacyGroups.sort(key=lambda obj: obj.parent_id)

def user_id(username): 
  user_newer = newerConnection.users.list(username=username)

  if not user_newer:
    user_legacy = legacyConnection.users.list(username=username)
    
    return newerConnection.users.create({
      'email': user_legacy[0].email,
      'password': 'z',
      'username': user_legacy[0].username,
      'name': user_legacy[0].name
    }).id
  else:
    return user_newer[0].id

controlGroups = {}

for group in newerConnection.groups.list(all=True):
  newerConnection.groups.delete(group.id)


for group in legacyGroups:
  print 'Criando grupo: ' + group.name

  if not group.parent_id:
    newGroupResponse = newerConnection.groups.create({
      'name' : group.name,
      'path' : group.path,
      'visibility': group.visibility
    })
  else:
    newGroupResponse = newerConnection.groups.create({
      'name' : group.name,
      'path' : group.path,
      'visibility': group.visibility,
      'parent_id': controlGroups[group.parent_id]
    })

  controlGroups[group.id] = newGroupResponse.id

  for member in group.members.list(all=True):
    newGroupResponse.members.create({
      'user_id' : user_id(member.username),
      'access_level': member.access_level
    })

  for project in group.projects.list(all=True):
    project = legacyConnection.projects.get(project.id)
    print 'Criando projeto: ' +  project.name

    newProjectResponse = newerConnection.projects.create({
      'name': project.name,
      'path': project.path,
      'visibility': project.visibility,
      'namespace_id': newGroupResponse.id,
      'default_branch': 'development'
    })
    for member in project.members.list(all=True):
      newProjectResponse.members.create({
        'user_id' : user_id(member.username),
        'access_level': member.access_level
      })

    os.system('git clone --mirror ' + project.ssh_url_to_repo + ' ./repos/' + project.path_with_namespace)
    os.system('git -C ' + os.path.dirname(os.path.realpath(__file__)) + '/repos/' + project.path_with_namespace + ' remote remove origin')
    os.system('git -C ' + os.path.dirname(os.path.realpath(__file__)) + '/repos/' + project.path_with_namespace + ' remote add origin ' + newProjectResponse.ssh_url_to_repo)
    os.system('git -C ' + os.path.dirname(os.path.realpath(__file__)) + '/repos/' + project.path_with_namespace + ' push --mirror')