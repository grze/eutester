# Software License Agreement (BSD License)
#
# Copyright (c) 2009-2011, Eucalyptus Systems, Inc.
# All rights reserved.
#
# Redistribution and use of this software in source and binary forms, with or
# without modification, are permitted provided that the following conditions
# are met:
#
#   Redistributions of source code must retain the above
#   copyright notice, this list of conditions and the
#   following disclaimer.
#
#   Redistributions in binary form must reproduce the above
#   copyright notice, this list of conditions and the
#   following disclaimer in the documentation and/or other
#   materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Author: matt.clark@eucalyptus.com
'''
Created on Mar 7, 2012
@author: clarkmatthew
Place holder class to provide convenience for testing, modifying, and retrieving Eucalyptus cloud property information
Intention is to reduce the time in looking up property names, and values outside of the eutester test lib, etc
Note: Debug output for the tester.sys command are controled by the eutester/eucaops object 

Sample:
cat my_cloud.conf
>   192.168.1.76	CENTOS	6.3	64	REPO	[CLC WS]
>   192.168.1.77	CENTOS	6.3	64	REPO	[SC00 CC00]
>   192.168.1.78	CENTOS	6.3	64	REPO	[NC00]


    from eucaops import Eucaops
    from eutester import euproperties
    Eucaops(config_file='my_cloud.conf', password='mypassword')

    ep_mgr = euproperties.Euproperty_Manager(tester,verbose=True, debugmethod=tester.debug)


#get some storage service properties, and some property values...

    #Get/Set value from dynamic method created in Euproperty_Manager...
        san_host_prop_value = ep_mgr.get_storage_sanhost_value()
        ep_mgr.set_storage_sanhost_value('192.168.1.200')

    #Get/set value from euproperty directly...
        san_host_prop = ep_mgr.get_property('san_host', 'storage', 'PARTI00')
        san_host_prop_value = san_host_prop.get()
        san_host_prop_set('192.168.1.200'

    #Get multiple properties at once based on certain filters...
        storage_properties = ep_mgr.get_properties(service_type='storage')
        partition1_properties = ep_mgr.get_properties(partition='partition1')

'''

import types
import re
import copy

class Euproperty_Type():
    authentication = 'authentication'
    autoscaling = 'autoscaling'
    bootstrap = 'bootstrap'
    cloud = 'cloud'
    cloudwatch = 'cloudwatch'
    cluster = 'cluster'
    dns ='dns'
    loadbalancing = 'loadbalancing'
    reporting = 'reporting'
    storage = 'storage'
    system = 'system'
    tagging = 'tagging'
    vmwarebroker = 'vmwarebroker'
    walrus = 'walrus'
    www = 'www'


    @classmethod
    def get_type_by_string(cls, typestring):
        try:
            if hasattr(cls, str(typestring)):
                return getattr(cls, str(typestring))
        except AttributeError, ae:
            print ('Property type:'+str(str)+" not defined, new property type?")
            raise ae


class Euproperty():
    def __init__(self, prop_mgr, property_string, service_type,  partition, name, value, mandatory=False, description=""):
        self.prop_mgr = prop_mgr
        self.service_type = Euproperty_Type.get_type_by_string(service_type)
        self.partition = partition
        self.name = name
        self.value = value
        self.property_string = property_string
        self.prop_mgr = prop_mgr
        self.lastvalue = value
        self.mandatory=mandatory
        
    def update(self):
        newprop = self.prop_mgr.update_property_list(property_name=self.property_string)[0]
        self = newprop

    def get(self):
        return self.value

    def set(self, value):
        return self.prop_mgr.set_property(self,value)

    def print_self(self, include_header=True, show_description=True, print_method=None, printout=True):
        if printout and not print_method:
            print_method = self.prop_mgr.debug
        name_len = 50
        service_len = 20
        part_len = 20
        value_len = 30
        line_len = 120
        ret = ""

        header = str('NAME').ljust(name_len)
        header += "|" + str('SERVICE TYPE').center(service_len)
        header += "|" + str('PARTITION').center(part_len)
        header += "|" + str('VALUE').center(value_len)
        header += "\n"

        out = str(self.name).ljust(name_len)
        out += "|" + str(self.service_type).center(service_len)
        out += "|" + str(self.partition).center(part_len)
        out += "|" + str(self.value).center(value_len)
        out += "\n"
        line="-"
        for x in xrange(0,line_len):
            line += "-"
        line += "\n"
        if include_header:
            ret = "\n"+line+header+line
        ret += out
        if show_description:
            ret += "DESCRIPTION: " + self.description + "\n"
        ret += line
        if print_method:
            print_method(ret)
        return ret

class Property_Map():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    
class Euproperty_Manager():
    tester = None
    verbose = False
    debugmethod = None
    
    def __init__(self, tester, verbose=False, machine=None, debugmethod=None):
        self.tester = tester
        self.debugmethod = debugmethod or tester.debug
        self.verbose = verbose
        self.work_machine =  machine or self.get_clc()
        self.access_key = self.tester.aws_access_key_id
        self.secret_key = self.tester.aws_secret_access_key
        self.service_url = 'http://'+str(self.tester.get_ec2_ip())+':8773/services/Eucalytpus'
        self.cmdpath = self.tester.eucapath+'/usr/sbin/'
        self.properties = []
        self.property_map = Property_Map()
        self.update_property_list()
        self.tester.property_manager = self
        
    def get_clc(self):
        return self.tester.service_manager.get_enabled_clc().machine   
        
    def debug(self,msg):
        '''
        simple method for printing debug. 
        msg - mandatory - string to be printed
        method - optional - callback to over ride default printing method 
        '''
        if (self.debugmethod is None):
            print (str(msg))
        else:
            self.debugmethod(msg)

    def show_all_authentication_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.authentication, partition=partition,debug_method=debug_method)

    def show_all_bootstrap_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.bootstrap, partition=partition,debug_method=debug_method)

    def show_all_cloud_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.cloud, partition=partition,debug_method=debug_method)

    def show_all_cluster_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.cluster, partition=partition,debug_method=debug_method)

    def show_all_reporting_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.reporting, partition=partition,debug_method=debug_method)

    def show_all_storage_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.storage, partition=partition,debug_method=debug_method)

    def show_all_system_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.system, partition=partition,debug_method=debug_method)

    def show_all_vmwarebroker_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.vmwarebroker, partition=partition,debug_method=debug_method)

    def show_all_walrus_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.walrus, partition=partition,debug_method=debug_method)

    def show_all_www_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.www, partition=partition,debug_method=debug_method)

    def show_all_autoscaling_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.autoscaling, partition=partition,debug_method=debug_method)

    def show_all_loadbalancing_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.loadbalancing, partition=partition,debug_method=debug_method)

    def show_all_tagging_properties(self,partition=None,debug_method=None):
        return self.show_all_properties(service_type=Euproperty_Type.tagging, partition=partition,debug_method=debug_method)


    def show_all_properties(self,
                            partition=None,
                            service_type=None,
                            value=None,
                            search_string=None,
                            list=None,
                            debug_method=None,
                            descriptions=True):
        debug_method = debug_method or self.debug
        list = list or self.get_properties(partition=partition,
                                           service_type=service_type,
                                           value=value,
                                           search_string=search_string)
        first = list.pop(0)
        buf = first.print_self(include_header=True, printout=False)
        count = 1
        last_service_type = first.service_type
        for prop in list:
            count += 1
            if prop.service_type != last_service_type:
                last_service_type = prop.service_type
                print_header = True
            else:
                print_header = False
            buf += prop.print_self(include_header=print_header, show_description=descriptions, printout=False)
        debug_method(buf)


    def get_properties(self,
                       partition=None,
                       service_type=None,
                       value=None,
                       search_string=None,
                       force_update=False):
        self.debug('get_properties: partition:' + str(partition) \
                                                + ", service_type:" + str(service_type) \
                                                + ", value:" + str(value) \
                                                + ", force_update:" +str(force_update))
        ret_props = []
        if not self.properties or force_update:
            self.update_property_list()
        properties = copy.copy(self.properties)
        if partition and properties:
            properties = self.get_all_properties_for_partition(partition, list=properties)
        if service_type and properties:
            properties = self.get_all_properties_for_service(service_type,list=properties)
        if search_string and properties:
            properties = self.get_all_properties_by_search_string(search_string, list=properties)
        if properties:
            if value:
                for prop in properties:
                    if prop.value == value:
                        ret_props.append(prop)
            else:
                ret_props.extend(properties)
        return ret_props

    def get_property(self,name,service_type, partition, force_update=False):
        self.debug('Get Property:' + str(name))
        ret_prop = None
        list = self.get_properties(partition=partition,service_type=service_type,force_update=force_update)
        if list:
            ret_prop =  self.get_euproperty_by_name(name, list=list)
        return ret_prop

    def update_property_list(self, property_name= ''):
        newlist = []
        newprop = None
        self.debug("updating property list...")
        cmdout = self.work_machine.sys(self.cmdpath+'euca-describe-properties -v -U ' + str(self.service_url) +
                                       ' -I ' + str(self.access_key) +
                                       ' -S ' + str(self.secret_key) +
                                       ' ' + property_name,
                                       code=0, verbose=self.verbose)
        for propstring in cmdout:
            try:
                if re.search("^PROPERTY", propstring):
                    newprop = self.parse_euproperty_from_string(propstring)

                elif newprop:
                    if re.search("^DESCRIPTION", propstring) and re.search(newprop.name, propstring):
                        newprop.description = self.parse_euproperty_description(propstring)
                    else:
                        newprop.value = str(newprop.value) + str(propstring)
            except Exception, e:
                self.debug('Error processing property line: ' + propstring)
                raise e
            if not newprop in newlist:
                newlist.append(newprop)
        if property_name:
            for newprop in newlist:
                for oldprop in self.properties:
                    if oldprop.property_string  == newprop.property_string:
                        oldprop = newprop
                        self.create_dynamic_property_map_from_property(newprop)
        else:
            self.properties = newlist
            self.property_map = Property_Map()
            for prop in self.properties:
                self.create_dynamic_property_map_from_property(prop)
        return newlist

    def parse_euproperty_description(self, propstring):
        '''
        Example string to parse: "DESCRIPTION	www.http_port	Listen to HTTP on this port."
        '''
        split = str(propstring).replace('DESCRIPTION','').split()
        description = " ".join(str(x) for x in split[1:])
        return str(description)

    def parse_property_value_from_string(self, propstring):
        split = str(propstring).replace('PROPERTY','').split()
        prop_value = " ".join(str(x) for x in split[1:])
        return str(prop_value)


                
    def parse_euproperty_from_string(self, propstring):
        '''
        Intended to convert a line of ouptut from euca-describe-properties into
        a euproperty. 
        :param str: line of output, example: "PROPERTY    walrus.storagemaxbucketsizeinmb    5120"
        :returns euproperty
        '''
        #self.debug('parse_euproperty_from_string, string:'+str(propstring))
        propstring = str(propstring).replace('PROPERTY','').strip()
        ret_service_type = None
        ret_partition = None
        splitstring = propstring.split()
        #get the property string, example: "walrus.storagemaxbucketsizeinmb"
        property_string = splitstring.pop(0)
        ret_value = " ".join(splitstring)
        #self.debug('property_string:'+str(property_string)+", ret_value:"+str(ret_value))
        #toss, property_string, ret_value = propstring.split()
        for prop in self.properties:
            #if this property is in our list, update the value and return
            if prop.property_string == property_string:
                prop.lastvalue = prop.value
                prop.value = ret_value
                return prop
        ret_name = property_string
        #...otherwise this property is not in our list yet, create a new property
        #parse property string into values...
        propattrs = property_string.split('.')

        #See if the first element is a partition
        partitions = self.tester.service_manager.get_all_partitions()

        for part in partitions:
            if part.name == propattrs[0]:
                #Assume this is the partition id/name, remove it from the propattrs list
                ret_partition = propattrs.pop(0)
                break
        #Move along items in list until we reach a service type
        for index in xrange(0,len(propattrs)):
            try:
                ret_service_type = Euproperty_Type.get_type_by_string(propattrs[index])
                propattrs.remove(propattrs[index])
                break
            except AttributeError:
                pass
            except IndexError:
                self.debug("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n" +
                           "Need to add new service? No service type found for: " + str(property_string) +
                           "\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                ret_service_type = propattrs.pop(0)

        #self.debug("ret_service_type: "+str(ret_service_type))

        #Store the name of the property
        ret_name = ".".join(propattrs)
        newprop = Euproperty(self, property_string, ret_service_type,  ret_partition, ret_name, ret_value)
        return newprop

    def create_dynamic_property_map_from_property(self, euproperty):
        context = self.property_map
        if not hasattr(context, 'all'):
            setattr(context, 'all', Property_Map())
        all_map = getattr(context, 'all')
        if euproperty.partition:
            if not hasattr(context, str(euproperty.partition)):
                setattr(context, str(euproperty.partition), Property_Map())
            context = getattr(context, str(euproperty.partition))
        if euproperty.service_type:
            if not hasattr(context, str(euproperty.service_type)):
                setattr(context, str(euproperty.service_type), Property_Map())
            context = getattr(context, str(euproperty.service_type))
        object_name = str(euproperty.service_type).replace('.','_') + "_" + str(euproperty.name).replace('.','_')
        if not hasattr(context,object_name):
            setattr(context, object_name, euproperty)
        if not hasattr(all_map, object_name):
            setattr(all_map, object_name, euproperty)



    def get_euproperty_by_name(self,name, list=None):
        props = []
        list = list or self.properties
        for property in list:
            if property.name == name:
                return property
        raise EupropertyNotFoundException('Property not found by name:'+str(name))
        
    def get_all_properties_for_partition(self, partition, list=None, verbose=False):
        self.debug('Get all properties for partition:'+str(partition))
        props = []
        list = list or self.properties
        for property in list:
            if property.partition == partition:
                if verbose:
                    self.debug('property:'+str(property.name)+", prop.partition:"+str(property.partition) +",partition:"+str(partition))
                props.append(property)
        self.debug('Returning list of len:'+str(len(props)))
        return props

    def get_all_properties_for_service(self,service, list=None):
        props = []
        list = list or self.properties
        for property in list:
            if property.service_type == service:
                props.append(property)
        return props

    def get_all_properties_by_search_string(self,search_string, list=None):
        props = []
        list = list or self.properties
        for property in list:
            if re.search(search_string,property.property_string):
                props.append(property)
        return props

    def set_property(self, property, value):
        if isinstance(property,Euproperty):

            return self.set_property_by_property_string(property.property_string, value)
        else:
            return self.set_property_by_property_string(str(property), value)

    def set_property(self,  property, value):
        '''
        Sets the property 'prop' at eucaops/eutester object 'tester' to 'value'    
        Returns new value  
        prop - mandatory - string representing the property to set
        value - mandatory - string representing the value to set the property to
        eucaops - optional - the eucaops/eutester object to set the property at
        '''
        value = str(value)
        if not isinstance(property,Euproperty):
            try:
                property = self.get_all_properties_by_search_string(property)
                if len(property) > 1:
                    raise Exception('More than one euproperty found for property string:' +str(property))
                else:
                    property = property[0]
            except Exception, e:
                raise Exception('Could not fetch property to set. Using string:' +str(property))
        property.lastvalue = property.value
        self.debug('Setting property('+property.property_string+') to value:'+str(value))
        ret_string = self.work_machine.sys(self.cmdpath+'euca-modify-property -U '+str(self.service_url)+' -I '+str(self.access_key)+' -S '+ str(self.secret_key) +' -p '+property.property_string+'='+str(value), code=0)[0]

        if (ret_string):
            ret_value= str(ret_string).split()[2]
        else:
            raise EupropertiesException("set_property output from modify was None")
        
        if (ret_value != value):
            raise EupropertiesException("set property("+property.property_string+") to value("+str(value)+") failed.Ret Value ("+str(ret_value)+")\nRet String\n"+ret_string)
        property.value = ret_value
        return ret_value

    def get_property_by_string(self, property_string):
        property = None
        for prop in self.properties:
            if prop.property_string == property_string:
                property = prop
                break
        return property

    def set_property_value_by_string(self, property_string, value):
        property = self.get_property_by_string(property_string)
        if not property:
            raise Exception('Property not found for:' + str(property_string))
        property.set(value)

    def get_property_value_by_string(self, property_string):
        property = self.get_property_by_string(property_string)
        if not property:
            raise Exception('Property not found for:' + str(property_string))
        return property.value

        
    def reset_property_to_default(self, prop):
        '''
        Sets a property 'prop' at eucaops/eutester object 'eucaops' to it's default value
        Returns new value
        prop - mandatory - string representing the property to set
        ucaops - optional - the eucaops/eutester object to set the property at
        '''

        if not isinstance(prop, Euproperty):
               prop = self.get_all_properties_by_search_string(prop)[0]
        property_string = prop.property_string
        prop.lastvalue = prop.value
        ret_string = str(self.work_machine.sys(self.cmdpath+'euca-modify-property -U '+str(self.service_url)+' -I '+str(self.access_key)+' -S '+ str(self.secret_key) +' -r '+str(property_string),code=0)[0])
        ret_value= ret_string.split()[2]
        self.debug('Reset property('+str(prop.name)+') to default value('+str(ret_value)+')')
        return ret_value
        
    def get_property_default_value(self, prop, ireadthewarning=False):
        '''
        Note: This hack method is intrusive! It will briefly reset the property
        This is a temporary method to get a properties default method
        prop - mandatory - string, eucalyptus property
        ireadthewarning - mandatory - boolean, to warn user this method is intrusive 
        '''
        if (ireadthewarning is False):
            raise EupropertiesException("ireadthewarning is set to false in get_property_default_value")
    
        original = prop.get()
        default = self.reset_property_to_default(prop)
        prop.set(original)
        return default
    
        
        
        
    '''
    ########################################################################
    STORAGE RELATED PROPERTY METHODS...
    ########################################################################
    '''

    '''
    #PARTI00.storage.maxvolumesizeingb
    def get_storage_maxvolumesizeingb(self,  zone='PARTI00'):
        value = self.get_property_value(  zone+'.storage.maxvolumesizeingb')
        return value
    
    def set_storage_maxvolumesizeingb(self, value, zone='PARTI00'):
        return self.set_property(  zone+'.storage.maxvolumesizeingb', value)
    
    #PARTI00.storage.maxtotalvolumesizeingb 
    def get_storage_maxtotalvolumesizeingb(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.maxtotalvolumesizeingb')
        return value
    
    def set_storage_maxtotalvolumesizeingb(self, value,  zone='PARTI00'):
        value = self.set_property(  zone+'.storage.maxtotalvolumesizeingb', value)
        return value
    
    #PARTI00.storage.zerofillvolumes 
    def get_storage_zerofillvolumes(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.zerofillvolumes')
        return value
    
    def set_storage_zerofillvolumes(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.zerofillvolumes', value)
        
    #PARTI00.storage.volumesdir 
    def get_storage_volumesdir(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.volumesdir')
        return value
    
    def set_storage_volumesdir(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.volumesdir', value)
        
    #PARTI00.storage.tid
    def get_storage_tid(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.tid')
        return value
    
    def set_storage_tid(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.tid', value)
    
    #PARTI00.storage.storeprefix
    def get_storage_storeprefix(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.storeprefix')
        return value
    
    def set_storage_storeprefix(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.storeprefix', value)
    
    #PARTI00.storageinterface
    def get_storageinterface(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.storageinterface')
        return value
    
    def set_storageinterface(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.storageinterface', value)
    
    #PARTI00.storage.snappercent
    def get_storage_snappercent(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.snappercent')
        return value
    
    def set_storage_snappercent(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.snappercent', value)
        
    #PARTI00.storage.shouldtransfersnapshots
    def get_storage_shouldtransfersnapshots(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.shouldtransfersnapshots')
        return value
    
    def set_storage_shouldtransfersnapshots(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.shouldtransfersnapshots', value)
        
    #PARTI00.storage.sanuser
    def get_storage_sanuser(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.sanuser')
        return value
    
    def set_storage_sanuser(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.sanuser', value)
    
    #PARTI00.storage.sanpassword
    def get_storage_sanpassword(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.sanpassword')
        return value
    
    def set_storage_sanpassword(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.sanpassword', value)
        
    #PARTI00.storage.sanhost
    def get_storage_sanhost(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.sanhost')
        return value
    
    def set_storage_sanhost(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.sanhost', value)
        
    #PARTI00.storage.minornumber
    def get_storage_minornumber(self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.minornumber')
        return value
    
    def set_storage_minornumber(self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.minornumber', value)
    
    #PARTI00.storage.majornumber 
    def get_storage_majornumber (self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.majornumber ')
        return value
    
    def set_storage_majornumber (self, value,  zone='PARTI00'):
        return self.set_property(  zone+'.storage.majornumber', value)
        
    #PARTI00.storage.dasdevice 
    def get_storage_dasdevice (self,   zone='PARTI00'): 
        value = self.get_property_value(  zone+'.storage.dasdevice')
        return value
    
    def set_storage_dasdevice (self, value,  zone='PARTI00'):
        if not isinstance(value, types.StringTypes):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.dasdevice ', value)
        
    def get_storage_activestoragegroupcleaning(self, zone='PARTI00'): #false
        return self.get_property_value(  zone+'.storage.activestoragegroupcleaning')
    
    def set_storage_activestoragegroupcleaning(self, boolean,  zone='PARTI00'):
        if not isinstance(boolean, types.BooleanType):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.activestoragegroupcleaning', boolean) 
    
    def get_storage_chapuser(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.chapuser')
    
    def set_storage_chapuser(self, string,  zone='PARTI00'):    #e4c6-1000
        if not isinstance(string, types.StringTypes):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.chapuser')
    
    def get_storage_blockstoragemanager(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.blockstoragemanager')
    
    def set_storage_blockstoragemanager(self, string,  zone='PARTI00'):    #e4c6-1000
        if not isinstance(string, types.StringTypes):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.blockstoragemanager')
    
    def get_storage_clipath(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.clipath')
    
    def set_storage_clipath(self, path,  zone='PARTI00'):    #/opt/Navisphere/bin/naviseccli
        if not isinstance(path, types.StringTypes):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.clipath')
        
    def get_storage_clonestoragegroup(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.clonestoragegroup')
   
    def set_storage_clonestoragegroup(self, string,  zone='PARTI00'):    #eucalyptus_clonelungroup
        if not isinstance(string, types.StringTypes):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.clonestoragegroup')
        
    def get_storage_loginscope(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.loginscope')
    
    def set_storage_loginscope(self, int,  zone='PARTI00'):    #0
        if not isinstance(int, types.IntType):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.loginscope')
        
    def get_storage_lunspallocator(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.lunspallocator')
    
    def set_storage_lunspallocator(self, string,  zone='PARTI00'):    #EmcVnxLunSpAllocatorByVolIdHash
        if not isinstance(string, types.StringTypes):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.lunspallocator')
        
    def get_storage_ncpaths(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.ncpaths')
    
    def set_storage_ncpaths(self, string,  zone='PARTI00'):    #iface0:192.168.25.182,iface1:10.109.25.186
        if not isinstance(string, types.StringTypes):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.ncpaths')
        
    def get_storage_quiescetimeseconds(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.quiescetimeseconds')
    
    def set_storage_quiescetimeseconds(self, int,  zone='PARTI00'):    #10
        if not isinstance(int, types.IntType):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.quiescetimeseconds')
        
    def get_storage_scpaths(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.scpaths')
    
    def set_storage_scpaths(self, string,  zone='PARTI00'):    #iface0:192.168.25.182,iface1:10.109.25.186
        if not isinstance(string, types.StringTypes):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.scpaths')
        
    def get_storage_storagepool(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.storagepool')
    
    def set_storage_storagepool(self, int,  zone='PARTI00'):    #0
        if not isinstance(int, types.IntType):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.storagepool')
        
    def get_storage_syncrate(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.syncrate')
    
    def set_storage_syncrate(self, string,  zone='PARTI00'):    #high
        if not isinstance(string, types.StringTypes):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.syncrate')
        
    def get_storage_timeoutinmillis(self, zone='PARTI00'):
        return self.get_property_value(  zone+'.storage.timeoutinmillis')
   
    def set_storage_timeoutinmillis(self, int,  zone='PARTI00'):    #<unset
        if not isinstance(int, types.IntType):
            raise Exception("Incorrect type passed")
        return self.set_property(  zone+'.storage.timeoutinmillis')

        
    '''


    ########################################################################
    #WALRUS RELATED PROPERTY METHODS...
    ########################################################################
    '''
    #walrus.storagemaxtotalsnapshotsizeingb 
    def get_walrus_storagemaxtotalsnapshotsizeingb(self, tester=None):
        value = self.get_property_value(  'walrus.storagemaxtotalsnapshotsizeingb')
        return value
    def set_walrus_storagemaxtotalsnapshotsizeingb(self, value, tester=None):
        return self.set_property(  'walrus.storagemaxtotalsnapshotsizeingb', value)
    '''
    
class EupropertiesException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__ (self):
        return repr(self.value)

class EupropertyNotFoundException(Exception):
    def __init__(self, value):
        self.value = value
def __str__ (self):
    return repr(self.value)

    
    